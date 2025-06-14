"""
Unit tests for data_processing.py
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_processing import (
    calculate_technical_indicators, calculate_price_statistics,
    calculate_fundamental_ratios, normalize_sector_metrics,
    calculate_cash_runway, analyze_debt_and_cash,
    process_stock_data, calculate_financial_ratios
)

class TestDataProcessing(unittest.TestCase):
    """Tests for the data_processing module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create sample price data
        dates = pd.date_range(start='2022-01-01', periods=200)
        
        # Define price pattern (uptrend, downtrend, flat)
        prices = np.concatenate([
            np.linspace(100, 150, 70),  # Uptrend
            np.linspace(150, 120, 80),  # Downtrend
            np.linspace(120, 125, 50)   # Slight uptrend
        ])
        
        self.price_data = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(prices))
        }, index=dates)
        
        # Create sample fundamental data
        self.fundamental_data = {
            'marketCap': 1000000000,
            'revenue': 250000000,
            'grossProfitTTM': 100000000,
            'totalAssets': 800000000,
            'totalDebt': 200000000,
            'totalCash': 150000000,
            'operatingCashflow': 80000000,
            'freeCashflow': 60000000,
            'ebitda': 90000000,
            'netIncome': 50000000,
            'eps': 2.5,
            'sharesOutstanding': 20000000,
            'bookValue': 30,
            'sector': 'Technology'
        }
        
        # Create multi-stock DataFrame for sector normalization
        self.multi_stock_df = pd.DataFrame([
            # Technology stocks
            {'symbol': 'AAPL', 'pe_ratio': 25, 'price_to_book': 15, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'pe_ratio': 30, 'price_to_book': 12, 'sector': 'Technology'},
            {'symbol': 'GOOGL', 'pe_ratio': 20, 'price_to_book': 8, 'sector': 'Technology'},
            # Healthcare stocks
            {'symbol': 'JNJ', 'pe_ratio': 18, 'price_to_book': 5, 'sector': 'Healthcare'},
            {'symbol': 'PFE', 'pe_ratio': 12, 'price_to_book': 3, 'sector': 'Healthcare'},
            # Energy stocks
            {'symbol': 'XOM', 'pe_ratio': 10, 'price_to_book': 2, 'sector': 'Energy'},
            {'symbol': 'CVX', 'pe_ratio': 8, 'price_to_book': 1.5, 'sector': 'Energy'},
        ])
        
        # Sample price data for process_stock_data test
        self.multi_symbol_price_data = {
            'AAPL': self.price_data.copy(),
            'MSFT': self.price_data.copy() * 1.5  # Different price scale
        }
        
        # Sample fundamental data for process_stock_data test
        self.multi_symbol_fundamental_data = {
            'AAPL': self.fundamental_data.copy(),
            'MSFT': {**self.fundamental_data.copy(), 'marketCap': 2000000000}
        }
    
    def test_calculate_technical_indicators(self):
        """Test technical indicator calculation."""
        result = calculate_technical_indicators(self.price_data.copy())
        
        # Check that key indicators were added
        self.assertIn('sma_20', result.columns)
        self.assertIn('sma_50', result.columns)
        self.assertIn('sma_200', result.columns)
        self.assertIn('ema_12', result.columns)
        self.assertIn('ema_26', result.columns)
        self.assertIn('macd', result.columns)
        self.assertIn('rsi', result.columns)
        
        # Check indicator values make sense
        # SMA should not be available for first N-1 rows
        self.assertTrue(pd.isna(result['sma_20'].iloc[0]))
        self.assertTrue(pd.isna(result['sma_20'].iloc[18]))
        self.assertFalse(pd.isna(result['sma_20'].iloc[19]))
        
        # RSI should be between 0 and 100
        rsi_vals = result['rsi'].dropna()
        self.assertTrue((rsi_vals >= 0).all() and (rsi_vals <= 100).all())
    
    def test_calculate_price_statistics(self):
        """Test price statistics calculation."""
        result = calculate_price_statistics(self.price_data.copy())
        
        # Check that key statistics were added
        self.assertIn('52w_high', result.columns)
        self.assertIn('52w_low', result.columns)
        self.assertIn('pct_off_52w_high', result.columns)
        self.assertIn('pct_off_52w_low', result.columns)
        self.assertIn('20d_vol', result.columns)
        
        # Check values make sense
        # All-time high should be 150
        self.assertAlmostEqual(result['52w_high'].iloc[-1], 150, delta=0.5)
        # All-time low should be 100
        self.assertAlmostEqual(result['52w_low'].iloc[-1], 100, delta=0.5)
        # Current price is 125, which is 16.7% off the high
        self.assertAlmostEqual(result['pct_off_52w_high'].iloc[-1], 16.7, delta=1)
        # Current price is 125, which is 25% above the low
        self.assertAlmostEqual(result['pct_off_52w_low'].iloc[-1], 25, delta=1)
    
    def test_calculate_fundamental_ratios(self):
        """Test fundamental ratio calculation."""
        result = calculate_fundamental_ratios(self.fundamental_data, self.fundamental_data)
        
        # Check that key ratios were calculated
        self.assertIn('pe_ratio', result)
        self.assertIn('price_to_book', result)
        self.assertIn('price_to_sales', result)
        self.assertIn('debt_to_equity', result)
        
        # Check values make sense
        # PE = marketCap / netIncome
        expected_pe = 1000000000 / 50000000
        self.assertAlmostEqual(result['pe_ratio'], expected_pe, delta=0.1)
        
        # Price to Book = marketCap / (bookValue * sharesOutstanding)
        expected_pb = 1000000000 / (30 * 20000000)
        self.assertAlmostEqual(result['price_to_book'], expected_pb, delta=0.1)
        
        # Price to Sales = marketCap / revenue
        expected_ps = 1000000000 / 250000000
        self.assertAlmostEqual(result['price_to_sales'], expected_ps, delta=0.1)
    
    def test_normalize_sector_metrics(self):
        """Test sector metric normalization."""
        result = normalize_sector_metrics(self.multi_stock_df.copy())
        
        # Check that new normalized columns were added
        self.assertIn('pe_ratio_sector_relative', result.columns)
        self.assertIn('price_to_book_sector_relative', result.columns)
        
        # Check normalization works correctly
        # Technology average P/E = (25 + 30 + 20) / 3 = 25
        # AAPL P/E = 25, normalized should be 25/25 = 1.0
        aapl_pe_norm = result.loc[result['symbol'] == 'AAPL', 'pe_ratio_sector_relative'].iloc[0]
        self.assertAlmostEqual(aapl_pe_norm, 1.0, delta=0.05)
        
        # MSFT P/E = 30, normalized should be 30/25 = 1.2
        msft_pe_norm = result.loc[result['symbol'] == 'MSFT', 'pe_ratio_sector_relative'].iloc[0]
        self.assertAlmostEqual(msft_pe_norm, 1.2, delta=0.05)
        
        # Healthcare average P/E = (18 + 12) / 2 = 15
        # JNJ P/E = 18, normalized should be 18/15 = 1.2
        jnj_pe_norm = result.loc[result['symbol'] == 'JNJ', 'pe_ratio_sector_relative'].iloc[0]
        self.assertAlmostEqual(jnj_pe_norm, 1.2, delta=0.05)
    
    def test_calculate_cash_runway(self):
        """Test cash runway calculation."""
        # Case 1: Positive cash flow (infinite runway)
        runway = calculate_cash_runway(100000000, -10000000)  # Cash of 100M, earning 10M/year
        self.assertEqual(runway, float('inf'))
        
        # Case 2: Zero cash flow
        runway = calculate_cash_runway(100000000, 0)
        self.assertEqual(runway, float('inf'))
        
        # Case 3: Negative cash flow (limited runway)
        runway = calculate_cash_runway(100000000, 10000000)  # Cash of 100M, burning 10M/year
        self.assertAlmostEqual(runway, 12, delta=0.1)  # 10 months of runway
    
    def test_analyze_debt_and_cash(self):
        """Test debt and cash analysis."""
        result = analyze_debt_and_cash(self.fundamental_data)
        
        # Check that key metrics were calculated
        self.assertIn('total_debt', result)
        self.assertIn('total_cash', result)
        self.assertIn('net_debt', result)
        self.assertIn('debt_to_equity', result)
        
        # Check calculations
        # Net debt = total_debt - total_cash
        expected_net_debt = 200000000 - 150000000
        self.assertEqual(result['net_debt'], expected_net_debt)
        
        # Debt to EBITDA = total_debt / ebitda
        expected_debt_to_ebitda = 200000000 / 90000000
        self.assertAlmostEqual(result['debt_to_ebitda'], expected_debt_to_ebitda, delta=0.01)
    
    @patch('data_processing.calculate_technical_indicators')
    @patch('data_processing.calculate_price_statistics')
    @patch('data_processing.calculate_fundamental_ratios')
    @patch('data_processing.analyze_debt_and_cash')
    @patch('data_processing.normalize_sector_metrics')
    def test_process_stock_data(self, mock_normalize, mock_analyze, mock_fund_ratios, 
                               mock_price_stats, mock_tech_indicators):
        """Test the main process_stock_data function."""
        # Configure mocks
        mock_tech_indicators.side_effect = lambda df: df.assign(sma_20=100, rsi=50)
        mock_price_stats.side_effect = lambda df: df.assign(pct_off_52w_high=10)
        mock_fund_ratios.return_value = {'pe_ratio': 20, 'price_to_book': 5}
        mock_analyze.return_value = {'total_debt': 100000000, 'total_cash': 200000000}
        mock_normalize.side_effect = lambda df: df.assign(pe_ratio_sector_relative=1.0)
        
        # Test
        result = process_stock_data(self.multi_symbol_price_data, self.multi_symbol_fundamental_data)
        
        # Verify
        self.assertIsInstance(result, pd.DataFrame)
        # Should have one row per stock (2 stocks)
        self.assertEqual(len(result), 2)
        # Should include symbols
        self.assertIn('symbol', result.columns)
        self.assertIn('AAPL', result['symbol'].values)
        self.assertIn('MSFT', result['symbol'].values)
        
        # All mock functions should have been called
        mock_tech_indicators.assert_called()
        mock_price_stats.assert_called()
        mock_fund_ratios.assert_called()
        mock_analyze.assert_called()
        mock_normalize.assert_called()
    
    @patch('data_processing.calculate_fundamental_ratios')
    def test_calculate_financial_ratios(self, mock_calc_ratios):
        """Test the calculate_financial_ratios function."""
        # Configure mock
        mock_calc_ratios.side_effect = lambda data, _: {
            'pe_ratio': 20 if data.get('symbol', '') == 'AAPL' else 25,
            'price_to_book': 5 if data.get('symbol', '') == 'AAPL' else 8
        }
        
        # Test
        result = calculate_financial_ratios(self.multi_symbol_fundamental_data)
        
        # Verify
        self.assertIsInstance(result, pd.DataFrame)
        # Should have one row per stock (2 stocks)
        self.assertEqual(len(result), 2)
        # Should include symbols
        self.assertIn('symbol', result.columns)
        self.assertIn('pe_ratio', result.columns)
        self.assertIn('price_to_book', result.columns)

if __name__ == '__main__':
    unittest.main()
