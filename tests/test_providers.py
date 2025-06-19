"""
Unit tests for individual data providers.

This test module tests only the relevant methods for each provider based on their
role in the application:

1. YFinance: Tests for market indexes and VIX data
2. Financial Modeling Prep: Tests for historical prices and fundamentals (primary provider)
3. Finnhub: Tests for company profile data

Each provider is tested only for the data types it's used for in the application.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_providers
from data_providers.yfinance_provider import YFinanceProvider
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider 
from data_providers.finnhub_provider import FinnhubProvider

class TestProviders(unittest.TestCase):
    """Tests for individual data providers."""
    
    def setUp(self):
        """
        Set up test environment.
        
        These tests require API keys to be properly configured in the environment.
        Tests will be skipped for providers where API keys are not available.
        
        YFinance provider doesn't require an API key and should always be available.
        """
        # Import config to check for API keys
        import config
        
        # Create real provider instances
        try:
            # YFinance doesn't need API key
            self.yf_provider = YFinanceProvider()
            self.yf_available = True
        except Exception as e:
            self.yf_available = False
            print(f"YFinance provider unavailable: {e}")
            
        try:
            # Check if FMP API key is configured
            if hasattr(config, 'FINANCIAL_MODELING_PREP_API_KEY') and config.FINANCIAL_MODELING_PREP_API_KEY:
                self.fmp_provider = FinancialModelingPrepProvider()
                self.fmp_available = True
            else:
                self.fmp_available = False
                print("Financial Modeling Prep API key not configured, skipping tests")
        except Exception as e:
            self.fmp_available = False
            print(f"Financial Modeling Prep provider unavailable: {e}")
            
        try:
            # Check if Finnhub API key is configured
            if hasattr(config, 'FINNHUB_API_KEY') and config.FINNHUB_API_KEY:
                self.finnhub_provider = FinnhubProvider()
                self.finnhub_available = True
            else:
                self.finnhub_available = False
                print("Finnhub API key not configured, skipping tests")
        except Exception as e:
            self.finnhub_available = False
            print(f"Finnhub provider unavailable: {e}")
    
    # YFinance Provider Tests
    #  - Used primarily for market indexes and VIX data    def test_yfinance_get_market_indexes(self):
        """Test YFinance provider for market indexes (primary use case)."""
        if not self.yf_available:
            self.skipTest("YFinance provider not available")
        
        # Test with S&P 500 index - YFinance is used specifically for market indexes
        result = self.yf_provider.get_historical_prices(['^GSPC'], period='5d', interval='1d')
        
        # Check the result structure
        self.assertIn('^GSPC', result)
        self.assertIsNotNone(result['^GSPC'])
        self.assertGreater(len(result['^GSPC']), 0)
        
        # Check the DataFrame structure
        df = result['^GSPC']
        
        # Handle MultiIndex columns format
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            # This is a MultiIndex DataFrame
            self.assertEqual(df.columns.names, ['Ticker', 'Price'])
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in expected_columns:
                self.assertIn(('^GSPC', col), df.columns)
        else:
            # Standard DataFrame format
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in expected_columns:
                self.assertIn(col, df.columns)
    
    def test_yfinance_get_vix_data(self):
        """Test YFinance provider for VIX data (primary use case)."""
        if not self.yf_available:
            self.skipTest("YFinance provider not available")
        
        # Test with VIX - YFinance is used specifically for VIX
        result = self.yf_provider.get_historical_prices(['^VIX'], period='5d', interval='1d')
        
        # Check the result structure
        self.assertIn('^VIX', result)
        self.assertIsNotNone(result['^VIX'])
        self.assertGreater(len(result['^VIX']), 0)
        
        # Check the DataFrame structure
        df = result['^VIX']
        
        # Handle MultiIndex columns format
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            # This is a MultiIndex DataFrame
            self.assertEqual(df.columns.names, ['Ticker', 'Price'])
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in expected_columns:
                self.assertIn(('^VIX', col), df.columns)
        else:
            # Standard DataFrame format
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in expected_columns:
                self.assertIn(col, df.columns)
    
    # Financial Modeling Prep Provider Tests
    #  - Primary provider for stock historical prices and fundamental data
    def test_fmp_get_historical_prices(self):
        """Test FinancialModelingPrep provider for stock historical prices."""
        if not self.fmp_available:
            self.skipTest("Financial Modeling Prep provider not available")
        
        # Test with Apple stock - FMP is the primary provider for stock data
        result = self.fmp_provider.get_historical_prices(['AAPL'], period='5d', interval='1d')
        
        # Check the result structure
        self.assertIn('AAPL', result)
        self.assertIsNotNone(result['AAPL'])
        self.assertGreater(len(result['AAPL']), 0)
        
        # Check the DataFrame structure
        df = result['AAPL']
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in expected_columns:
            self.assertIn(col, df.columns)
    
    def test_fmp_get_company_overview(self):
        """Test FinancialModelingPrep provider for company overview data."""
        if not self.fmp_available:
            self.skipTest("Financial Modeling Prep provider not available")
        
        # Test with Apple stock - FMP is used for fundamental data
        result = self.fmp_provider.get_company_overview('AAPL')
        
        # Check basic company information
        self.assertIsNotNone(result)
        self.assertIn('Symbol', result)
        self.assertEqual(result['Symbol'], 'AAPL')
        self.assertIn('Name', result)
        self.assertIn('Sector', result)
    
    def test_fmp_get_income_statement(self):
        """Test FinancialModelingPrep provider for income statement data."""
        if not self.fmp_available:
            self.skipTest("Financial Modeling Prep provider not available")
        
        # Test with Apple stock - FMP is used for financial statements
        result = self.fmp_provider.get_income_statement('AAPL')
        
        # Check the result structure
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        # Check for key columns
        expected_columns = ['fiscalDateEnding', 'totalRevenue', 'grossProfit', 'netIncome']
        for col in expected_columns:
            self.assertIn(col, result.columns)
    
    def test_fmp_get_balance_sheet(self):
        """Test FinancialModelingPrep provider for balance sheet data."""
        if not self.fmp_available:
            self.skipTest("Financial Modeling Prep provider not available")
        
        # Test with Apple stock - FMP is used for financial statements
        result = self.fmp_provider.get_balance_sheet('AAPL')
        
        # Check the result structure
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        # Check for key columns
        expected_columns = ['fiscalDateEnding', 'totalAssets', 'totalLiabilities', 'totalShareholderEquity']
        for col in expected_columns:
            self.assertIn(col, result.columns)
    
    def test_fmp_get_cash_flow(self):
        """Test FinancialModelingPrep provider for cash flow data."""
        if not self.fmp_available:
            self.skipTest("Financial Modeling Prep provider not available")
        
        # Test with Apple stock - FMP is used for financial statements
        result = self.fmp_provider.get_cash_flow('AAPL')
        
        # Check the result structure
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        # Check for key columns
        expected_columns = ['fiscalDateEnding', 'operatingCashflow', 'capitalExpenditures', 'freeCashflow']
        for col in expected_columns:
            self.assertIn(col, result.columns)
            
    # Finnhub Provider Tests
    #  - Used for company profile data
    def test_finnhub_get_company_overview(self):
        """Test Finnhub provider for company overview data."""
        if not self.finnhub_available:
            self.skipTest("Finnhub provider not available")
        
        # Test with Apple stock
        result = self.finnhub_provider.get_company_overview('AAPL')
        
        # Check basic company information
        self.assertIsNotNone(result)
        self.assertIn('Symbol', result)
        self.assertEqual(result['Symbol'], 'AAPL')
        self.assertIn('Name', result)
    
    # Default Provider Test
    def test_default_provider_selection(self):
        """Test that the default provider is Financial Modeling Prep."""
        default_provider = data_providers.get_provider()
        self.assertEqual(default_provider.get_provider_name(), "FinancialModelingPrepProvider")

if __name__ == '__main__':
    unittest.main()
