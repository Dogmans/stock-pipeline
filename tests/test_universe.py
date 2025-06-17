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
import universe  # Import the full module
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
        self.assertTrue('gics_sector' in result.columns)        # Verify the mock was called
        mock_read_html.assert_called_once()
        
    def test_get_russell2000_symbols_from_cache(self):
        """Test retrieving Russell 2000 symbols from cache."""
        # Let's use a different approach - we'll create a temporary file
        # and verify the function can load from it
        import tempfile
        import os
        
        # Create temporary test data and save it to a file
        original_russell_file = os.path.join(config.DATA_DIR, 'russell2000.csv')
        temp_df = self.sample_russell.copy()
        
        # Override the russell2000.csv path temporarily for testing
        with patch('universe.os.path.join', return_value=original_russell_file):
            with patch('os.path.exists', return_value=True):
                with patch('pandas.read_csv', return_value=temp_df) as mock_read_csv:
                    # Call function with force_refresh=False to use cache
                    result = get_russell2000_symbols(force_refresh=False)
                    
                    # Verify read_csv was called
                    mock_read_csv.assert_called_once_with(original_russell_file)
        
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
    def test_get_stock_universe_sp500(self):
        """Test getting SP500 universe."""
        # Test using live data instead of mocks
        result = get_stock_universe("sp500")
        
        # Verify results - we're just testing the structure and that we get actual data
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(len(result) > 0, "Should return at least some stocks")
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
    def test_get_stock_universe_all(self):
        """Test getting combined universe."""
        # Test using live data instead of mocks
        result = get_stock_universe("all")
        
        # Verify results - we're just testing the structure and that we get actual data
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(len(result) > 0, "Should return at least some stocks")
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
        
        # Make sure the combined universe is larger than any individual universe
        sp500 = get_stock_universe("sp500")
        self.assertTrue(len(result) >= len(sp500), "Combined universe should be at least as large as SP500")

if __name__ == '__main__':
    unittest.main()
