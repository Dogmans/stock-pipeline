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
            'Volume': np.random.randint(2000000000, 5000000000, 90)
        }, index=sp500_dates)
        
        # Dow Jones sample data - in decline but not correction
        dow_dates = pd.date_range(start='2022-01-01', periods=90)
        dow_close = np.linspace(36000, 33500, 90)  # 6.9% decline
        self.market_data['^DJI'] = pd.DataFrame({
            'Close': dow_close,
            'High': [36000] * 90,
            'Low': [33000] * 90,
            'Volume': np.random.randint(400000000, 800000000, 90)
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
    
    @patch('yfinance.download')
    def test_get_market_conditions(self, mock_yf_download):
        """Test retrieving market conditions data."""
        # Configure mock
        def mock_download(tickers, *args, **kwargs):
            if isinstance(tickers, str):
                tickers = [tickers]
            
            result = {}
            for ticker in tickers:
                if ticker in self.market_data:
                    result[ticker] = self.market_data[ticker]
                else:
                    # Return empty DataFrame for unknown tickers
                    result[ticker] = pd.DataFrame()
            
            # If a single ticker was requested, return the DataFrame directly
            if len(result) == 1:
                return result[tickers[0]]
            
            # For multiple tickers, combine into a multi-index DataFrame
            combined = pd.concat(result, names=['Ticker', 'Date'])
            return combined
        
        mock_yf_download.side_effect = mock_download
        
        # Test
        result = get_market_conditions(force_refresh=True)
        
        # Verify
        self.assertIsInstance(result, dict)
        self.assertIn('^GSPC', result)  # S&P 500
        self.assertIn('^VIX', result)   # VIX
        
        # Check that the function calculated the correct period returns
        self.assertIn('1d_return', result['^GSPC'].columns)
        self.assertIn('1m_return', result['^GSPC'].columns)
        self.assertIn('3m_return', result['^GSPC'].columns)
        self.assertIn('ytd_return', result['^GSPC'].columns)
        self.assertIn('max_drawdown', result['^GSPC'].columns)
    
    @patch('market_data.get_market_conditions')
    def test_is_market_in_correction(self, mock_get_conditions):
        """Test detecting market correction status."""
        # Configure mock to return our test data with S&P 500 in correction
        mock_get_conditions.return_value = {
            '^GSPC': self.market_data['^GSPC'].copy(),
            '^DJI': self.market_data['^DJI'].copy(),
            '^VIX': self.market_data['^VIX'].copy()
        }
        
        # Add necessary metrics
        for ticker in ['^GSPC', '^DJI']:
            # Calculate max_drawdown manually
            high = self.market_data[ticker]['High'].max()
            last = self.market_data[ticker]['Close'].iloc[-1]
            drawdown = (high - last) / high * 100
            
            # Add to DataFrame
            self.market_data[ticker]['max_drawdown'] = drawdown
            self.market_data[ticker]['1m_return'] = -5  # 5% decline in last month
        
        # Test
        is_correction, status_text = is_market_in_correction(force_refresh=True)
        
        # Verify
        self.assertTrue(is_correction)  # S&P 500 is down 12% from peak
        self.assertIn("correction", status_text.lower())  # Status text should mention correction
    
    @patch('yfinance.download')
    def test_get_sector_performances(self, mock_yf_download):
        """Test retrieving sector performance data."""
        # Configure mock
        def mock_download(tickers, *args, **kwargs):
            if isinstance(tickers, str):
                tickers = [tickers]
            
            result = {}
            for ticker in tickers:
                if ticker in self.sector_data:
                    result[ticker] = self.sector_data[ticker]
                else:
                    # Return empty DataFrame for unknown tickers
                    result[ticker] = pd.DataFrame()
            
            # If a single ticker was requested, return the DataFrame directly
            if len(result) == 1:
                return result[tickers[0]]
            
            # For multiple tickers, combine into a multi-index DataFrame
            combined = pd.concat(result, names=['Ticker', 'Date'])
            return combined
        
        mock_yf_download.side_effect = mock_download
        
        # Test
        result = get_sector_performances(force_refresh=True)
        
        # Verify
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('1m_return', result.columns)
        self.assertIn('3m_return', result.columns)
        self.assertIn('ytd_return', result.columns)
        
        # Check sector names in index
        self.assertIn('Energy', result.index)
        self.assertIn('Financials', result.index)
        
        # Check performance ordering - Energy should be top performer
        self.assertEqual(result['ytd_return'].idxmax(), 'Energy')
        # Financials should be worst performer
        self.assertEqual(result['ytd_return'].idxmin(), 'Financials')

if __name__ == '__main__':
    unittest.main()
