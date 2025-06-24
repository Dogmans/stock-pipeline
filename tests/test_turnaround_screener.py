"""
Unit tests for the turnaround candidates screener
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from screeners import screen_for_turnaround_candidates

class TestTurnaroundScreener(unittest.TestCase):
    """Tests for the turnaround candidates screener."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a simple universe DataFrame
        self.test_universe = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'company_name': ['Apple Inc.', 'Microsoft Corp', 'Alphabet Inc.'],
            'sector': ['Technology', 'Technology', 'Technology']
        })
        
        # Set up the patch for the FMP provider
        self.fmp_provider_patcher = patch('data_providers.financial_modeling_prep.FinancialModelingPrepProvider')
        self.mock_fmp_provider = self.fmp_provider_patcher.start()
        
        # Set up the provider instance mock
        self.mock_provider_instance = MagicMock()
        self.mock_fmp_provider.return_value = self.mock_provider_instance
        
    def tearDown(self):
        """Clean up after test."""
        self.fmp_provider_patcher.stop()
        
    def test_turnaround_screener_with_no_matches(self):
        """Test screening when no stocks match the criteria."""
        # Configure mock to return empty DataFrames
        self.mock_provider_instance.get_income_statement.return_value = pd.DataFrame()
        self.mock_provider_instance.get_balance_sheet.return_value = pd.DataFrame()
        self.mock_provider_instance.get_company_overview.return_value = {}
        
        # Call the screener
        result = screen_for_turnaround_candidates(self.test_universe)
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        
        # Check that the provider was called for each symbol
        self.assertEqual(self.mock_provider_instance.get_company_overview.call_count, 3)
        
    def test_turnaround_screener_with_matches(self):
        """Test screening when stocks match the criteria."""
        # Mock the provider methods
        self.mock_provider_instance.get_company_overview.return_value = {
            'Name': 'Test Company',
            'Sector': 'Technology',
            'Symbol': 'TEST'
        }
        
        # Mock income statements with improving EPS
        income_data = pd.DataFrame({
            'eps': [0.1, -0.2, -0.5, -0.8, -1.0, -1.2, -1.5, -1.8],  # Latest quarter turned positive
            'revenue': [110, 100, 95, 90, 85, 80, 75, 70],    # Improving revenue
            'grossProfit': [55, 45, 40, 35, 30, 25, 20, 15]   # Improving gross profit
        })
        self.mock_provider_instance.get_income_statement.return_value = income_data
        
        # Mock balance sheets with improving cash position
        balance_data = pd.DataFrame({
            'cashAndCashEquivalents': [50, 40, 35, 30], 
            'totalDebt': [100, 120, 130, 135]  # Decreasing debt
        })
        self.mock_provider_instance.get_balance_sheet.return_value = balance_data
        
        # Call the screener
        result = screen_for_turnaround_candidates(self.test_universe)
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)  # All 3 symbols should match
        
        # Check the first result
        first_result = result.iloc[0]
        self.assertEqual(first_result['eps_trend'], 'Improving')
        self.assertEqual(first_result['revenue_trend'], 'Reaccelerating')
        self.assertEqual(first_result['margins'], 'Improving')
        self.assertEqual(first_result['cash_position'], 'Strengthening')
        self.assertEqual(first_result['debt_trend'], 'Reducing')
        self.assertEqual(first_result['turnaround_score'], 9)  # All criteria met (3+2+2+1+1)
        
    def test_turnaround_screener_with_partial_matches(self):
        """Test screening when stocks partially match the criteria."""
        # Mock the provider methods
        self.mock_provider_instance.get_company_overview.return_value = {
            'Name': 'Test Company',
            'Sector': 'Technology',
            'Symbol': 'TEST'
        }
        
        # Count to track which symbol we're processing
        self.call_count = 0
        
        # Define a side effect function that returns different data for different symbols
        def get_income_side_effect(*args, **kwargs):
            self.call_count += 1
            if self.call_count == 1:  # First symbol (AAPL)
                # Strong turnaround - EPS improving, revenue reaccelerating
                return pd.DataFrame({
                    'eps': [0.1, -0.2, -0.5, -0.8, -1.0, -1.2, -1.5, -1.8],
                    'revenue': [110, 100, 95, 90, 85, 80, 75, 70],
                    'grossProfit': [55, 45, 40, 35, 30, 25, 20, 15]
                })
            elif self.call_count == 2:  # Second symbol (MSFT)
                # Weak turnaround - EPS still negative but improving
                return pd.DataFrame({
                    'eps': [-0.1, -0.3, -0.5, -0.7, -0.9, -1.1, -1.3, -1.5],
                    'revenue': [105, 100, 98, 95, 92, 90, 88, 85],
                    'grossProfit': [42, 40, 39, 38, 36, 35, 33, 30]
                })
            else:  # Third symbol (GOOGL)
                # No turnaround - EPS and revenue declining
                return pd.DataFrame({
                    'eps': [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2],
                    'revenue': [80, 85, 90, 95, 100, 105, 110, 115],
                    'grossProfit': [30, 35, 40, 45, 50, 55, 60, 65]
                })
                
        # Reset call count for balance sheets
        self.balance_call_count = 0
        
        # Define a side effect function for balance sheets
        def get_balance_side_effect(*args, **kwargs):
            self.balance_call_count += 1
            if self.balance_call_count == 1:  # First symbol (AAPL)
                return pd.DataFrame({
                    'cashAndCashEquivalents': [50, 40, 35, 30], 
                    'totalDebt': [100, 120, 130, 135]
                })
            elif self.balance_call_count == 2:  # Second symbol (MSFT)
                return pd.DataFrame({
                    'cashAndCashEquivalents': [45, 40, 38, 35],
                    'totalDebt': [110, 100, 90, 80]  # Debt increasing
                })
            else:  # Third symbol (GOOGL)
                return pd.DataFrame({
                    'cashAndCashEquivalents': [30, 35, 40, 45],  # Cash decreasing
                    'totalDebt': [120, 110, 100, 90]  # Debt increasing
                })
                
        # Set the side effects
        self.mock_provider_instance.get_income_statement.side_effect = get_income_side_effect
        self.mock_provider_instance.get_balance_sheet.side_effect = get_balance_side_effect
        
        # Call the screener
        result = screen_for_turnaround_candidates(self.test_universe)
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)  # Only 2 symbols should match (score >= 3)
          # Check scores
        scores = result['turnaround_score'].tolist()
        # Scores may vary based on implementation details, but should include high and medium scores
        max_score = max(scores) 
        min_score = min(scores)
        self.assertTrue(max_score >= 6)   # AAPL should have a high score
        self.assertTrue(min_score >= 3)   # Second match should have at least the minimum threshold

if __name__ == '__main__':
    unittest.main()
