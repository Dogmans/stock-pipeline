"""
Unit tests for stock_data.py
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stock_data import (
    get_historical_prices, get_fundamental_data, fetch_52_week_lows
)

class TestStockData(unittest.TestCase):
    """Tests for the stock_data module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create sample price data
        dates = pd.date_range(start='2022-01-01', periods=365)
        
        # AAPL sample data
        self.aapl_data = pd.DataFrame({
            'Open': np.random.normal(150, 5, len(dates)),
            'High': np.random.normal(155, 5, len(dates)),
            'Low': np.random.normal(145, 5, len(dates)),
            'Close': np.random.normal(152, 5, len(dates)),
            'Volume': np.random.randint(50000000, 100000000, len(dates))
        }, index=dates)
        
        # MSFT sample data
        self.msft_data = pd.DataFrame({
            'Open': np.random.normal(250, 10, len(dates)),
            'High': np.random.normal(255, 10, len(dates)),
            'Low': np.random.normal(245, 10, len(dates)),
            'Close': np.random.normal(252, 10, len(dates)),
            'Volume': np.random.randint(30000000, 60000000, len(dates))
        }, index=dates)
        
        # Sample fundamental data
        self.fundamental_data = {
            'AAPL': {
                'Symbol': 'AAPL',
                'Name': 'Apple Inc.',
                'MarketCapitalization': 2500000000000,
                'PERatio': 25.5,
                'DividendYield': 0.6,
                'BookValue': 4.5,
                'EPS': 6.15,
                'Revenue': 365000000000,
                'GrossProfitTTM': 152000000000
            },
            'MSFT': {
                'Symbol': 'MSFT',
                'Name': 'Microsoft Corporation',
                'MarketCapitalization': 2200000000000,
                'PERatio': 28.2,
                'DividendYield': 0.8,
                'BookValue': 17.4,
                'EPS': 9.65,
                'Revenue': 168000000000,
                'GrossProfitTTM': 115000000000
            }
        }
    
    @patch('yfinance.download')
    def test_get_historical_prices(self, mock_yf_download):
        """Test retrieving historical price data."""
        # Configure mock
        def mock_download(*args, **kwargs):
            tickers = kwargs.get('tickers', [])
            if len(tickers) == 1:
                if tickers[0] == 'AAPL':
                    return self.aapl_data
                elif tickers[0] == 'MSFT':
                    return self.msft_data
            else:
                # For multiple tickers, yfinance returns a multi-index DataFrame
                # Simulate this behavior
                aapl_copy = self.aapl_data.copy()
                msft_copy = self.msft_data.copy()
                
                # Add symbol level to index
                aapl_copy = aapl_copy.assign(Symbol='AAPL')
                msft_copy = msft_copy.assign(Symbol='MSFT')
                
                # Combine
                combined = pd.concat([aapl_copy, msft_copy])
                return combined
        
        mock_yf_download.side_effect = mock_download
        
        # Test single symbol
        result_single = get_historical_prices(['AAPL'], force_refresh=True)
        self.assertIn('AAPL', result_single)
        self.assertIsInstance(result_single['AAPL'], pd.DataFrame)
        
        # Test multiple symbols
        result_multi = get_historical_prices(['AAPL', 'MSFT'], force_refresh=True)
        self.assertIn('AAPL', result_multi)
        self.assertIn('MSFT', result_multi)
        self.assertIsInstance(result_multi['AAPL'], pd.DataFrame)
        self.assertIsInstance(result_multi['MSFT'], pd.DataFrame)
    
    @patch('alpha_vantage.fundamentaldata.FundamentalData')
    @patch('yfinance.Ticker')
    def test_get_fundamental_data(self, mock_yf_ticker, mock_av_fundamental):
        """Test retrieving fundamental data."""
        # Configure YF mock
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = self.fundamental_data['AAPL']
        mock_yf_ticker.return_value = mock_ticker_instance
        
        # Configure AV mock
        mock_av_instance = MagicMock()
        mock_av_instance.get_company_overview.return_value = (
            {'Symbol': 'AAPL', 'PERatio': '25.5'}, None
        )
        mock_av_instance.get_income_statement_annual.return_value = (
            {'annualReports': [{'fiscalDateEnding': '2022-09-30', 'grossProfit': '152000000000'}]}, None
        )
        mock_av_instance.get_balance_sheet_annual.return_value = (
            {'annualReports': [{'fiscalDateEnding': '2022-09-30', 'totalAssets': '350000000000'}]}, None
        )
        mock_av_instance.get_cash_flow_annual.return_value = (
            {'annualReports': [{'fiscalDateEnding': '2022-09-30', 'operatingCashflow': '120000000000'}]}, None
        )
        mock_av_fundamental.return_value = mock_av_instance
        
        # Test
        result = get_fundamental_data(['AAPL'], force_refresh=True)
        
        # Verify
        self.assertIn('AAPL', result)
        self.assertIsInstance(result['AAPL'], dict)
        self.assertIn('MarketCapitalization', result['AAPL'])
    
    @patch('stock_data.get_stock_universe')
    @patch('stock_data.get_historical_prices')
    def test_fetch_52_week_lows(self, mock_get_prices, mock_get_universe):
        """Test fetching stocks near 52-week lows."""
        # Configure mocks
        mock_get_universe.return_value = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'security': ['Apple Inc.', 'Microsoft Corp', 'Alphabet Inc.']
        })
        
        # Create price data where AAPL is near its 52-week low
        # and others are not
        dates = pd.date_range(start='2022-01-01', periods=365)
        
        aapl_data = pd.DataFrame({
            'Close': [90] * 364 + [95],  # Current price 95, min 90 (5.6% above low)
            'Volume': [50000000] * 365
        }, index=dates)
        
        msft_data = pd.DataFrame({
            'Close': [200] * 364 + [280],  # Current price 280, min 200 (40% above low)
            'Volume': [40000000] * 365
        }, index=dates)
        
        googl_data = pd.DataFrame({
            'Close': [1000] * 364 + [1500],  # Current price 1500, min 1000 (50% above low)
            'Volume': [20000000] * 365
        }, index=dates)
        
        mock_get_prices.return_value = {
            'AAPL': aapl_data,
            'MSFT': msft_data,
            'GOOGL': googl_data
        }
        
        # Test
        result = fetch_52_week_lows(force_refresh=True)
        
        # Verify
        self.assertIsInstance(result, pd.DataFrame)
        # AAPL should be in results (within 15% of 52-week low)
        self.assertIn('AAPL', result['symbol'].values)
        # MSFT and GOOGL should not be in results
        self.assertNotIn('MSFT', result['symbol'].values)
        self.assertNotIn('GOOGL', result['symbol'].values)

if __name__ == '__main__':
    unittest.main()
