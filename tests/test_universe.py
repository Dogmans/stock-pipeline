"""
Unit tests for universe.py

This test module has been updated to:
1. Use actual API calls for real-world testing
2. Keep tests simple and straightforward
3. Use appropriate timeouts for API calls
"""

import unittest
import pandas as pd
import time

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
import universe
from universe import (
    get_sp500_symbols, get_russell2000_symbols, 
    get_nasdaq100_symbols, get_stock_universe
)

class TestUniverse(unittest.TestCase):
    """Tests for the universe module."""
    
    def test_get_sp500_symbols(self):
        """Test retrieving S&P 500 symbols from the real API."""
        # Use force_refresh=True to ensure we get fresh data
        result = get_sp500_symbols(force_refresh=True)
        
        # Basic validation of the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0, "Should return S&P 500 stocks")
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
        
        # Check for some well-known S&P 500 companies
        all_symbols = set(result['symbol'].tolist())
        expected_symbols = {'AAPL', 'MSFT', 'GOOGL'}
        # At least one of these major companies should be in S&P 500
        self.assertTrue(any(symbol in all_symbols for symbol in expected_symbols))
    
    def test_get_russell2000_symbols(self):
        """Test retrieving Russell 2000 symbols from iShares ETF holdings."""
        # Use force_refresh=True to ensure we get fresh data
        result = get_russell2000_symbols(force_refresh=True)
        
        # Basic validation of the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0, "Should return Russell 2000 stocks")
        
        # Verify the required columns exist
        required_columns = ['symbol', 'security', 'gics_sector', 'gics_sub-industry']
        for column in required_columns:
            self.assertTrue(column in result.columns, f"Column {column} should be present")

    def test_get_nasdaq100_symbols(self):
        """Test retrieving NASDAQ 100 symbols."""
        # Use force_refresh=True to ensure we get fresh data
        result = get_nasdaq100_symbols(force_refresh=True)
        
        # Basic validation of the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0, "Should return NASDAQ 100 stocks")
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
        
    def test_get_stock_universe_sp500(self):
        """Test getting SP500 universe."""
        # Use a small timeout to avoid long test times
        result = get_stock_universe("sp500")
        
        # Basic validation of the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0, "Should return SP500 stocks")
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)
    
    def test_get_stock_universe_all(self):
        """Test getting combined universe."""
        # Skip this test if it would take too long
        if not config.FINNHUB_API_KEY:
            self.skipTest("No Finnhub API key available for Russell 2000 data")
            
        # Get the combined universe
        result = get_stock_universe("all")
        
        # Basic validation of the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0, "Should return stock universe")
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('security' in result.columns)

if __name__ == '__main__':
    unittest.main()
