"""
Test the turnaround screener with sample data
"""
import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
# Updated import to use new screeners package structure
from screeners.turnaround_candidates import screen_for_turnaround_candidates

class TestTurnaroundScreener(unittest.TestCase):
    
    @patch('screeners.FinancialModelingPrepProvider')
    def test_turnaround_detection(self, mock_provider_class):
        """Test that the screener correctly identifies a turnaround company"""
        # Create mock provider
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        # Create mock data
        # 1. Company overview data
        mock_provider.get_company_overview.return_value = {
            'Name': 'Turnaround Corp',
            'Sector': 'Technology'
        }
        
        # 2. Income statement with EPS going from negative to positive
        mock_income = pd.DataFrame({
            'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
            'eps': [-0.40, -0.30, -0.20, -0.10, 0.05, 0.15, 0.25, 0.35],
            'revenue': [80, 85, 90, 95, 100, 105, 110, 120],
            'grossProfit': [16, 18, 20, 22, 25, 28, 31, 36]
        })
        # Reverse to have most recent first
        mock_income = mock_income.iloc[::-1].reset_index(drop=True)
        mock_provider.get_income_statement.return_value = mock_income
        
        # 3. Balance sheet with improving cash
        mock_balance = pd.DataFrame({
            'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
            'cash': [50, 48, 45, 40, 38, 35, 33, 30],
            'totalDebt': [100, 105, 110, 120, 125, 130, 120, 110]
        })
        # Reverse to have most recent first
        mock_balance = mock_balance.iloc[::-1].reset_index(drop=True)
        mock_provider.get_balance_sheet.return_value = mock_balance
        
        # Create test universe
        universe_df = pd.DataFrame({'symbol': ['TEST']})
        
        # Run the screener
        results = screen_for_turnaround_candidates(universe_df)
        
        # Verify results
        self.assertFalse(results.empty, "Should detect the turnaround")
        self.assertEqual(results.iloc[0]['symbol'], 'TEST')
        self.assertTrue('Negative-to-Positive EPS' in results.iloc[0]['eps_trend'])
        self.assertGreaterEqual(results.iloc[0]['turnaround_score'], 5)
        
    @patch('screeners.FinancialModelingPrepProvider')
    def test_non_turnaround_detection(self, mock_provider_class):
        """Test that the screener correctly rejects a non-turnaround company"""
        # Create mock provider
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        # Create mock data
        # 1. Company overview data
        mock_provider.get_company_overview.return_value = {
            'Name': 'Steady Corp',
            'Sector': 'Technology'
        }
        
        # 2. Income statement with consistently positive EPS
        mock_income = pd.DataFrame({
            'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
            'eps': [0.40, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47],
            'revenue': [100, 101, 102, 103, 104, 105, 106, 107],
            'grossProfit': [25, 25, 25, 25, 25, 25, 25, 25]
        })
        # Reverse to have most recent first
        mock_income = mock_income.iloc[::-1].reset_index(drop=True)
        mock_provider.get_income_statement.return_value = mock_income
        
        # 3. Balance sheet with steady metrics
        mock_balance = pd.DataFrame({
            'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
            'cash': [50, 50, 50, 50, 50, 50, 50, 50],
            'totalDebt': [100, 100, 100, 100, 100, 100, 100, 100]
        })
        # Reverse to have most recent first
        mock_balance = mock_balance.iloc[::-1].reset_index(drop=True)
        mock_provider.get_balance_sheet.return_value = mock_balance
        
        # Create test universe
        universe_df = pd.DataFrame({'symbol': ['TEST']})
        
        # Run the screener
        results = screen_for_turnaround_candidates(universe_df)
        
        # Verify results - should not detect as turnaround
        self.assertTrue(results.empty, "Should not detect a turnaround")

if __name__ == '__main__':
    unittest.main()
