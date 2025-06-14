"""
Unit tests for screeners.py
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from screeners import (
    get_available_screeners, run_all_screeners,
    price_to_book_screener, pe_ratio_screener, fifty_two_week_low_screener
)

class TestScreeners(unittest.TestCase):
    """Tests for the screeners module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create sample stock data with various characteristics
        self.processed_data = pd.DataFrame([
            # Value stock - Low P/B, Low P/E
            {'symbol': 'XOM', 'close': 80, 'pe_ratio': 8.0, 'price_to_book': 1.2, 
             'pct_off_52w_high': 25, 'pct_off_52w_low': 20,
             'sector': 'Energy', 'security': 'Exxon Mobil Corp'},
            
            # Growth stock - High P/B, High P/E
            {'symbol': 'TSLA', 'close': 800, 'pe_ratio': 100.0, 'price_to_book': 25.0, 
             'pct_off_52w_high': 30, 'pct_off_52w_low': 50,
             'sector': 'Consumer Discretionary', 'security': 'Tesla Inc'},
            
            # Near 52-week low stock
            {'symbol': 'INTC', 'close': 35, 'pe_ratio': 9.0, 'price_to_book': 1.5, 
             'pct_off_52w_high': 45, 'pct_off_52w_low': 8,
             'sector': 'Technology', 'security': 'Intel Corp'},
            
            # Cash-rich biotech (no earnings, high price-to-book but lots of cash)
            {'symbol': 'BIIB', 'close': 200, 'pe_ratio': float('nan'), 'price_to_book': 3.5,
             'pct_off_52w_high': 35, 'pct_off_52w_low': 15,
             'sector': 'Healthcare', 'security': 'Biogen Inc',
             'cash_to_market_cap': 0.8, 'total_cash': 8000000000}
        ])
        
        # Fundamental ratios for financial metrics
        self.financial_ratios = pd.DataFrame([
            {'symbol': 'XOM', 'pe_ratio': 8.0, 'price_to_book': 1.2, 'debt_to_equity': 0.3},
            {'symbol': 'TSLA', 'pe_ratio': 100.0, 'price_to_book': 25.0, 'debt_to_equity': 0.5},
            {'symbol': 'INTC', 'pe_ratio': 9.0, 'price_to_book': 1.5, 'debt_to_equity': 0.4},
            {'symbol': 'BIIB', 'pe_ratio': float('nan'), 'price_to_book': 3.5, 'debt_to_equity': 0.2}
        ])
        
        # Market data for context
        self.market_data = {
            '^GSPC': pd.DataFrame({
                'Close': [4500],
                'max_drawdown': [12.5],  # In correction territory
                '1m_return': [-8.0],
                '3m_return': [-15.0]
            }),
            '^VIX': pd.DataFrame({
                'Close': [28.5]  # Elevated but not extreme
            })
        }
        
        # Universe data
        self.universe_data = pd.DataFrame([
            {'symbol': 'XOM', 'security': 'Exxon Mobil Corp', 'gics_sector': 'Energy'},
            {'symbol': 'TSLA', 'security': 'Tesla Inc', 'gics_sector': 'Consumer Discretionary'},
            {'symbol': 'INTC', 'security': 'Intel Corp', 'gics_sector': 'Information Technology'},
            {'symbol': 'BIIB', 'security': 'Biogen Inc', 'gics_sector': 'Health Care'}
        ])
    
    def test_get_available_screeners(self):
        """Test getting available screeners."""
        screeners = get_available_screeners()
        # Check that core screeners are included
        self.assertIn('price_to_book', screeners)
        self.assertIn('pe_ratio', screeners)
        self.assertIn('52_week_lows', screeners)
        # Verify return type
        self.assertIsInstance(screeners, list)
    
    def test_price_to_book_screener(self):
        """Test the price-to-book screener."""
        # Test the screener
        result = price_to_book_screener(self.processed_data, self.financial_ratios)
        
        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        # Only XOM should pass the screen (P/B < 1.2)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['symbol'], 'XOM')
        # Result should include reason for selection
        self.assertIn('reason', result.columns)
    
    def test_pe_ratio_screener(self):
        """Test the P/E ratio screener."""
        # Test the screener
        result = pe_ratio_screener(self.processed_data, self.financial_ratios)
        
        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        # XOM and INTC should pass (P/E < 10)
        self.assertEqual(len(result), 2)
        self.assertIn('XOM', result['symbol'].values)
        self.assertIn('INTC', result['symbol'].values)
        # TSLA should not pass (P/E too high)
        self.assertNotIn('TSLA', result['symbol'].values)
        # BIIB should not pass (P/E is NaN)
        self.assertNotIn('BIIB', result['symbol'].values)
    
    def test_52_week_low_screener(self):
        """Test the 52-week low screener."""
        # Test the screener
        result = fifty_two_week_low_screener(self.processed_data, self.financial_ratios)
        
        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        # Only INTC should pass (within 10% of 52-week low)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['symbol'], 'INTC')
    
    @patch('screeners.get_available_screeners')
    def test_run_all_screeners(self, mock_get_available):
        """Test running all screeners."""
        # Configure mock
        mock_get_available.return_value = [
            'price_to_book', 'pe_ratio', '52_week_lows'
        ]
        
        # Test running all screeners
        results = run_all_screeners(
            self.processed_data,
            self.financial_ratios,
            self.market_data,
            self.universe_data
        )
        
        # Verify
        self.assertIsInstance(results, dict)
        self.assertIn('price_to_book', results)
        self.assertIn('pe_ratio', results)
        self.assertIn('52_week_lows', results)
        
        # Check that each screener returned the expected results
        self.assertEqual(len(results['price_to_book']), 1)  # XOM only
        self.assertEqual(len(results['pe_ratio']), 2)       # XOM and INTC
        self.assertEqual(len(results['52_week_lows']), 1)   # INTC only
    
    @patch('screeners.get_available_screeners')
    def test_run_specific_screeners(self, mock_get_available):
        """Test running specific screeners."""
        # Configure mock
        mock_get_available.return_value = [
            'price_to_book', 'pe_ratio', '52_week_lows'
        ]
        
        # Test running just the price_to_book screener
        results = run_all_screeners(
            self.processed_data,
            self.financial_ratios,
            self.market_data,
            self.universe_data,
            strategies=['price_to_book']
        )
        
        # Verify
        self.assertIsInstance(results, dict)
        self.assertIn('price_to_book', results)
        self.assertNotIn('pe_ratio', results)
        self.assertNotIn('52_week_lows', results)
        
        # Check correct results
        self.assertEqual(len(results['price_to_book']), 1)  # XOM only
        self.assertEqual(results['price_to_book'].iloc[0]['symbol'], 'XOM')

if __name__ == '__main__':
    unittest.main()
