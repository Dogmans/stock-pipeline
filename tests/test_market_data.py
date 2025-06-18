"""
Unit tests for market_data.py
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from market_data import (
    get_market_conditions, is_market_in_correction, get_sector_performances
)
import data_providers

class TestMarketData(unittest.TestCase):
    """Tests for the market_data module."""
    
    def setUp(self):
        """Set up test environment."""
        # Sample market index data
        self.market_data = {}
        
        # S&P 500 sample data - in correction (more than 10% off high)
        sp500_dates = pd.date_range(start='2022-01-01', periods=90)
        sp500_close = np.linspace(5000, 4400, 90)  # 12% decline
        self.market_data['^GSPC'] = pd.DataFrame({
            'Close': sp500_close,
            'High': [5000] * 90,
            'Low': [4400] * 90,
            'Volume': np.random.randint(2000000, 5000000, 90)
        }, index=sp500_dates)
        
        # Dow Jones sample data - in decline but not correction
        dow_dates = pd.date_range(start='2022-01-01', periods=90)
        dow_close = np.linspace(36000, 33500, 90)  # 6.9% decline
        self.market_data['^DJI'] = pd.DataFrame({
            'Close': dow_close,
            'High': [36000] * 90,
            'Low': [33000] * 90,
            'Volume': np.random.randint(400000, 800000, 90)
        }, index=dow_dates)
        
        # VIX sample data - elevated but not extreme
        vix_dates = pd.date_range(start='2022-01-01', periods=90)
        vix_close = np.random.normal(25, 3, 90)  # Around 25, elevated but not extreme
        self.market_data['^VIX'] = pd.DataFrame({
            'Close': vix_close,
            'High': [40] * 90,
            'Low': [15] * 90,
        }, index=vix_dates)
        
        # Sector data
        self.sector_data = {}
        sector_etfs = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY']
        sector_dates = pd.date_range(start='2022-01-01', periods=90)
        
        for etf in sector_etfs:
            if etf == 'XLE':  # Energy outperforming
                perf = 0.15  # +15%
            elif etf == 'XLF':  # Financials underperforming
                perf = -0.18  # -18%
            else:
                perf = np.random.uniform(-0.10, 0.10)  # Random between -10% and +10%
                
            start_price = 100
            end_price = start_price * (1 + perf)
            self.sector_data[etf] = pd.DataFrame({
                'Close': np.linspace(start_price, end_price, 90),
                'High': [max(start_price, end_price) * 1.05] * 90,
                'Low': [min(start_price, end_price) * 0.95] * 90,
                'Volume': np.random.randint(5000000, 20000000, 90)
            }, index=sector_dates)
    
    def test_get_market_conditions(self):
        """Test retrieving market conditions data."""
        # Create a mock data provider
        mock_provider = MagicMock()
        
        # Create test data
        mock_sp500_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [101, 102, 103],
            'Adj Close': [101, 102, 103],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range(start='2023-01-01', periods=3))
        
        # Setup the mock provider to return our test data
        mock_provider.get_historical_prices.return_value = {
            '^GSPC': mock_sp500_data.copy(),
            '^DJI': mock_sp500_data.copy(),
            '^IXIC': mock_sp500_data.copy(),
            '^VIX': mock_sp500_data.copy(),
            'XLK': mock_sp500_data.copy(),
            'XLF': mock_sp500_data.copy(),
        }
        
        # Mock the provider name
        mock_provider.get_provider_name.return_value = 'Test Provider'
        
        # Test with our mock provider
        result = get_market_conditions(data_provider=mock_provider, force_refresh=True)
        
        # Verify basic structure
        self.assertIsInstance(result, dict)
        # We should have some market data
        self.assertTrue(len(result) > 0, "Should have at least some market data")
        
        # Check if one of the values is a DataFrame
        if len(result) > 0:
            first_key = next(iter(result))
            self.assertIsInstance(result[first_key], pd.DataFrame)
            # Ensure the DataFrame has basic expected columns
            self.assertIn('Close', result[first_key].columns)
              # Make sure our mock was called with the expected parameters
        mock_provider.get_historical_prices.assert_called()
    
    def test_is_market_in_correction(self):
        """Test detecting market correction status."""
        # Create a mock data provider
        mock_provider = MagicMock()
        
        # Create a mock VIX response with a high value indicating correction
        mock_vix_data = pd.DataFrame({
            'Open': [28, 30, 32],
            'High': [30, 32, 35],
            'Low': [27, 28, 30],
            'Close': [29, 31, 33],  # VIX at 33 is high, indicating correction territory
            'Adj Close': [29, 31, 33],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range(start='2023-01-01', periods=3))
        
        # Configure the mock provider to return high VIX values
        mock_provider.get_historical_prices.return_value = {
            "^VIX": mock_vix_data
        }
        
        # Mock the provider name
        mock_provider.get_provider_name.return_value = 'Test Provider'
        
        # We need to patch the config to make sure our threshold matches our test data
        with patch('market_data.config') as mock_config:
            # Set VIX threshold to 30 so our test value of 33 triggers correction
            mock_config.VIX_CORRECTION_THRESHOLD = 30
            mock_config.VIX_BLACK_SWAN_THRESHOLD = 40
            
            # Test
            is_correction, status_text = is_market_in_correction(data_provider=mock_provider, force_refresh=True)
            
            # Verify
            self.assertTrue(is_correction)  # VIX is at 33, above the 30 threshold
            self.assertIn("correction", status_text.lower())  # Status should mention correction
              # Make sure our mock was called with the expected parameters
        mock_provider.get_historical_prices.assert_called()
    
    def test_get_sector_performances(self):
        """Test retrieving sector performance data."""
        # Create a mock data provider
        mock_provider = MagicMock()
        
        # Configure mock to return our sector data directly
        mock_provider.get_historical_prices.return_value = self.sector_data
        
        # Mock the provider name
        mock_provider.get_provider_name.return_value = 'Test Provider'
        
        # Test
        result = get_sector_performances(data_provider=mock_provider, force_refresh=True)
        
        # Verify we got a DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        
        # Verify we have all sectors
        if not result.empty:
            # Check for XLE (energy) and XLF (financials)
            self.assertIn('XLE', result['etf'].values)
            self.assertIn('XLF', result['etf'].values)
            
            # Check that sectors are sorted by performance (1_month_change)
            # XLF should be at the top (worst performer at -18%)
            self.assertEqual(result.iloc[0]['etf'], 'XLF')
            
            # Check required columns
            self.assertIn('sector', result.columns)
            self.assertIn('price', result.columns)
            self.assertIn('1_week_change', result.columns)
            self.assertIn('1_month_change', result.columns)
              # Make sure our mock was called with the expected parameters
        mock_provider.get_historical_prices.assert_called()
    
    def test_get_market_conditions_simple(self):
        """Test retrieving market conditions data using simple mocks."""
        # Create a mock data provider
        mock_provider = MagicMock()
        
        # Create a simplified DataFrame
        mock_sp500_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [101, 102, 103],
            'Adj Close': [101, 102, 103],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range(start='2023-01-01', periods=3))
        
        # Create mock VIX data too
        mock_vix_data = pd.DataFrame({
            'Open': [20, 21, 22],
            'High': [25, 26, 27],
            'Low': [15, 16, 17],
            'Close': [21, 22, 23],
            'Adj Close': [21, 22, 23],
            'Volume': [10000, 11000, 12000]
        }, index=pd.date_range(start='2023-01-01', periods=3))
          # Setup mock provider to return our test data
        market_data = {}
        
        # Add S&P 500
        market_data['^GSPC'] = mock_sp500_data.copy()
        
        # Add Dow Jones
        market_data['^DJI'] = mock_sp500_data.copy()
        
        # Add NASDAQ
        market_data['^IXIC'] = mock_sp500_data.copy()
        
        # Add VIX
        market_data['^VIX'] = mock_vix_data.copy()
        
        # Add sector ETFs
        for etf in config.SECTOR_ETFS.keys():
            market_data[etf] = mock_sp500_data.copy()
        
        # Configure the mock provider to return our data
        mock_provider.get_historical_prices.return_value = market_data
        mock_provider.get_provider_name.return_value = 'Test Provider'
        
        # Test with our mock provider
        result = get_market_conditions(data_provider=mock_provider, force_refresh=True)
        
        # Verify basics
        self.assertIsInstance(result, dict)
        self.assertTrue(len(result) > 0, "Should have at least some market data")
        
        # Check if '^GSPC' or other index is in result
        found_index = False
        for key in result:
            if key == '^GSPC' or key == 'VIX' or key.startswith('^'):
                found_index = True
                break
        
        self.assertTrue(found_index, "Should have at least one market index in result")        # Check that the data is not empty where present
        for key, df in result.items():
            self.assertFalse(df.empty, f"DataFrame for {key} should not be empty")
    
    def test_market_data_structure(self):
        """Test that market data functions return expected types and don't crash."""
        # Test get_market_conditions - just make sure it returns a dict and doesn't crash
        market_conditions = get_market_conditions()
        self.assertIsInstance(market_conditions, dict)
        
        # Test is_market_in_correction - just make sure it returns a tuple with bool and string
        is_correction, status = is_market_in_correction()
        self.assertIsInstance(is_correction, bool)
        self.assertIsInstance(status, str)
        
        # Test get_sector_performances - just make sure it returns a DataFrame
        sector_perf = get_sector_performances()
        self.assertIsInstance(sector_perf, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
