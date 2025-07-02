"""
Unit tests for the new screener architecture where each screener fetches its own data.
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Updated imports to use new screeners package structure
from screeners.utils import get_available_screeners, run_all_screeners
from screeners.price_to_book import screen_for_price_to_book
from screeners.pe_ratio import screen_for_pe_ratio
from screeners.fifty_two_week_lows import screen_for_52_week_lows

class TestNewScreeners(unittest.TestCase):
    """Tests for the new screener architecture."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a minimal stock universe
        self.universe_df = pd.DataFrame([
            {'symbol': 'AAPL', 'security': 'Apple Inc', 'gics_sector': 'Information Technology', 'gics_sub-industry': 'Technology Hardware, Storage & Peripherals'},
            {'symbol': 'MSFT', 'security': 'Microsoft Corp', 'gics_sector': 'Information Technology', 'gics_sub-industry': 'Software'},
            {'symbol': 'XOM', 'security': 'Exxon Mobil Corp', 'gics_sector': 'Energy', 'gics_sub-industry': 'Integrated Oil & Gas'},
        ])
        
    @patch('data_providers.financial_modeling_prep.FinancialModelingPrepProvider')
    def test_pe_ratio_screener(self, mock_fmp):
        """Test the P/E ratio screener with the new architecture."""
        # Setup the mock
        mock_provider = mock_fmp.return_value
        
        # Mock company overview data for AAPL
        mock_provider.get_company_overview.side_effect = lambda symbol: {
            'AAPL': {'PERatio': '25.6', 'MarketCapitalization': 2500000000000, 'Name': 'Apple Inc', 'Sector': 'Technology', 'price': 180.0, 'EPS': '7.0'},
            'MSFT': {'PERatio': '35.2', 'MarketCapitalization': 2400000000000, 'Name': 'Microsoft Corp', 'Sector': 'Technology', 'price': 330.0, 'EPS': '9.5'},
            'XOM': {'PERatio': '8.5', 'MarketCapitalization': 450000000000, 'Name': 'Exxon Mobil Corp', 'Sector': 'Energy', 'price': 115.0, 'EPS': '13.5'},
        }.get(symbol, {})
        
        # Mock historical prices
        mock_provider.get_historical_prices.side_effect = lambda symbol, period: {
            'AAPL': pd.DataFrame({'Close': [178.0, 179.5, 180.0]}, index=['2023-11-20', '2023-11-21', '2023-11-22']),
            'MSFT': pd.DataFrame({'Close': [325.0, 328.0, 330.0]}, index=['2023-11-20', '2023-11-21', '2023-11-22']),
            'XOM': pd.DataFrame({'Close': [112.0, 114.5, 115.0]}, index=['2023-11-20', '2023-11-21', '2023-11-22']),
        } if symbol in ['AAPL', 'MSFT', 'XOM'] else {}
        
        # Call the screener with just the universe
        result = screen_for_pe_ratio(universe_df=self.universe_df, max_pe=15.0)
        
        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)  # Updated to expect all stocks with valid P/E ratios
        
        # Find the XOM row
        xom_row = result[result['symbol'] == 'XOM'].iloc[0]
        self.assertEqual(xom_row['symbol'], 'XOM')
        self.assertTrue(xom_row['meets_threshold'])  # Check that XOM meets the threshold
        self.assertIn('reason', result.columns)
        self.assertTrue('Low P/E ratio' in xom_row['reason'])
        
    @patch('data_providers.financial_modeling_prep.FinancialModelingPrepProvider')
    def test_run_all_screeners(self, mock_fmp):
        """Test running all screeners with the new architecture."""
        # Setup the mock
        mock_provider = mock_fmp.return_value
        
        # Mock relevant provider methods for testing
        # Mock company overview data
        mock_provider.get_company_overview.side_effect = lambda symbol: {
            'AAPL': {'PERatio': '25.6', 'PriceToBookRatio': '15.8', 'MarketCapitalization': 2500000000000, 'Name': 'Apple Inc', 'Sector': 'Technology'},
            'MSFT': {'PERatio': '35.2', 'PriceToBookRatio': '12.5', 'MarketCapitalization': 2400000000000, 'Name': 'Microsoft Corp', 'Sector': 'Technology'},
            'XOM': {'PERatio': '8.5', 'PriceToBookRatio': '1.2', 'MarketCapitalization': 450000000000, 'Name': 'Exxon Mobil Corp', 'Sector': 'Energy'},
        }.get(symbol, {})
        
        # Mock historical prices
        mock_provider.get_historical_prices.return_value = {
            'AAPL': pd.DataFrame({'Close': [178.0, 179.5, 180.0]}, index=['2023-11-20', '2023-11-21', '2023-11-22']),
            'MSFT': pd.DataFrame({'Close': [325.0, 328.0, 330.0]}, index=['2023-11-20', '2023-11-21', '2023-11-22']),
            'XOM': pd.DataFrame({'Close': [112.0, 114.5, 115.0]}, index=['2023-11-20', '2023-11-21', '2023-11-22']),
        }
        
        # Define test strategies
        test_strategies = ['pe_ratio', 'price_to_book']
        
        # Mock get_available_screeners to return only our test strategies
        with patch('screeners.get_available_screeners', return_value=test_strategies):
            # Run all screeners
            results = run_all_screeners(universe_df=self.universe_df, strategies=test_strategies)
            
            # Verify results
            self.assertIsInstance(results, dict)
            self.assertEqual(len(results), 3)  # Updated to include combined
            self.assertIn('pe_ratio', results)
            self.assertIn('price_to_book', results)
            self.assertIn('combined', results)
            
            # Verify PE ratio results
            pe_results = results['pe_ratio']
            self.assertGreaterEqual(len(pe_results), 1)  # At least one result
            
            # Verify that XOM is in pe_results and meets the threshold
            xom_in_pe = any(row['symbol'] == 'XOM' and row['meets_threshold'] 
                           for _, row in pe_results.iterrows())
            self.assertTrue(xom_in_pe)

if __name__ == '__main__':
    unittest.main()
