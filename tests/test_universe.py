"""
Unit tests for universe.py
"""

import unittest
import pandas as pd
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from universe import (
    get_sp500_symbols, get_russell2000_symbols, 
    get_nasdaq100_symbols, get_stock_universe
)

class TestUniverse(unittest.TestCase):
    """Tests for the universe module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create sample data for mocks
        self.sample_sp500 = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'security': ['Apple Inc.', 'Microsoft Corp', 'Alphabet Inc.'],
            'gics_sector': ['IT', 'IT', 'Communication Services'],
            'gics_sub-industry': ['Tech Hardware', 'Software', 'Interactive Media']
        })
        
        self.sample_russell = pd.DataFrame({
            'symbol': ['FROG', 'PLTR', 'DDOG'],
            'security': ['JFrog Ltd', 'Palantir', 'Datadog Inc'],
            'gics_sector': ['', '', ''],
            'gics_sub-industry': ['', '', '']
        })
        
        self.sample_nasdaq = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'AMZN'],
            'security': ['Apple Inc.', 'Microsoft Corp', 'Amazon.com Inc.'],
            'gics_sector': ['IT', 'IT', 'Consumer Discretionary'],
            'gics_sub-industry': ['Tech Hardware', 'Software', 'Internet Retail']
        })
    
    @patch('universe.pd.read_html')
    def test_get_sp500_symbols(self, mock_read_html):
        """Test retrieving S&P 500 symbols."""
        # Set up mock
        mock_table = MagicMock()
        mock_table.columns = ['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry']
        mock_table.__getitem__.return_value = pd.Series(['AAPL', 'MSFT'])  # For symbol column
        
        # Convert mock_table to DataFrame with our sample data
        mock_read_html.return_value = [self.sample_sp500.copy()]
        
        # Call function
        result = get_sp500_symbols(force_refresh=True)
        
        # Verify
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
        self.assertTrue('gics_sector' in result.columns)
        
        # Verify the mock was called
        mock_read_html.assert_called_once()
    
    @patch('os.path.exists')
    @patch('pd.read_csv')
    @patch('finnhub.Client')
    def test_get_russell2000_symbols_from_cache(self, mock_finnhub, mock_read_csv, mock_exists):
        """Test retrieving Russell 2000 symbols from cache."""
        # Configure mocks
        mock_exists.return_value = True
        mock_read_csv.return_value = self.sample_russell.copy()
        
        # Call function
        result = get_russell2000_symbols()
        
        # Verify
        mock_exists.assert_called_once()
        mock_read_csv.assert_called_once()
        mock_finnhub.assert_not_called()  # Should not call Finnhub if cache exists
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertTrue('symbol' in result.columns)
    
    @patch('os.path.exists')
    @patch('finnhub.Client')
    def test_get_russell2000_symbols_from_api(self, mock_finnhub, mock_exists):
        """Test retrieving Russell 2000 symbols from API."""
        # Configure mocks
        mock_exists.return_value = False
        mock_client = MagicMock()
        mock_client.indices_const.return_value = {
            'constituents': ['FROG', 'PLTR', 'DDOG']
        }
        mock_finnhub.return_value = mock_client
        
        # Set API key in config
        original_key = config.FINNHUB_API_KEY
        config.FINNHUB_API_KEY = 'dummy_key'
        
        try:
            # Call function
            result = get_russell2000_symbols(force_refresh=True)
            
            # Verify
            mock_exists.assert_called_once()
            mock_finnhub.assert_called_once_with(api_key='dummy_key')
            mock_client.indices_const.assert_called_once_with(symbol='^RUT')
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 3)
            self.assertTrue('symbol' in result.columns)
        finally:
            # Restore config
            config.FINNHUB_API_KEY = original_key
    
    @patch('universe.pd.read_html')
    def test_get_nasdaq100_symbols(self, mock_read_html):
        """Test retrieving NASDAQ 100 symbols."""
        # Set up mock
        mock_read_html.return_value = [
            pd.DataFrame(),  # First table that doesn't match
            self.sample_nasdaq.copy()  # Second table with Ticker and Company columns
        ]
        
        # Rename columns to match what the function expects
        self.sample_nasdaq.columns = ['Ticker', 'Company', 'GICS Sector', 'GICS Sub-Industry']
        
        # Call function
        result = get_nasdaq100_symbols(force_refresh=True)
        
        # Verify
        mock_read_html.assert_called_once()
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
    
    @patch('universe.get_sp500_symbols')
    @patch('universe.get_russell2000_symbols')
    @patch('universe.get_nasdaq100_symbols')
    def test_get_stock_universe_sp500(self, mock_nasdaq, mock_russell, mock_sp500):
        """Test getting SP500 universe."""
        mock_sp500.return_value = self.sample_sp500.copy()
        
        result = get_stock_universe('sp500')
        
        mock_sp500.assert_called_once()
        mock_russell.assert_not_called()
        mock_nasdaq.assert_not_called()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
    
    @patch('universe.get_sp500_symbols')
    @patch('universe.get_russell2000_symbols')
    @patch('universe.get_nasdaq100_symbols')
    def test_get_stock_universe_all(self, mock_nasdaq, mock_russell, mock_sp500):
        """Test getting combined universe."""
        mock_sp500.return_value = self.sample_sp500.copy()
        mock_russell.return_value = self.sample_russell.copy()
        mock_nasdaq.return_value = self.sample_nasdaq.copy()
        
        result = get_stock_universe('all')
        
        mock_sp500.assert_called_once()
        mock_russell.assert_called_once()
        mock_nasdaq.assert_called_once()
        
        self.assertIsInstance(result, pd.DataFrame)
        # After removing duplicates, we should have 5 unique symbols
        # AAPL and MSFT appear in both SP500 and NASDAQ
        self.assertEqual(len(result), 5)

if __name__ == '__main__':
    unittest.main()
