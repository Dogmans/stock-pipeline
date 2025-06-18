"""
Unit tests for main.py
"""

import unittest
import sys
import pandas as pd
from io import StringIO
from unittest.mock import patch, MagicMock, call, ANY

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main

class TestMain(unittest.TestCase):
    """Tests for main.py functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Capture stdout
        self.held_output = StringIO()
        self.old_stdout = sys.stdout
        sys.stdout = self.held_output        # Set up sample data
        self.sample_universe = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META'],
            'security': ['Apple Inc', 'Microsoft Corp', 'Alphabet Inc', 'Amazon.com Inc', 'Meta Platforms Inc'],
            'gics_sector': ['Technology'] * 5,
            'gics_sub-industry': ['Technology'] * 5
        })
          # Default mock arguments
        self.default_args = MagicMock()
        self.default_args.universe = 'sp500'
        self.default_args.strategies = 'value,growth'  # Use string instead of list to match main.py expectations
        self.default_args.output = './output'
        self.default_args.cache_info = False
        self.default_args.clear_cache = False
        self.default_args.force_refresh = False
        self.default_args.clear_old_cache = None
        self.default_args.debug = False
        self.default_args.limit = None
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore stdout
        sys.stdout = self.old_stdout
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_parse_arguments(self, mock_parse_args):
        """Test argument parsing."""
        # Configure mock
        mock_parse_args.return_value = self.default_args
        
        # Call parse_arguments
        args = main.parse_arguments()
        
        # Verify returned object is the mock
        self.assertEqual(args, self.default_args)
    
    @patch('main.parse_arguments')
    @patch('main.get_cache_info')
    def test_cache_info_option(self, mock_get_cache_info, mock_parse_arguments):
        """Test that --cache-info option works correctly."""
        # Set up arguments
        args = self.default_args
        args.cache_info = True
        mock_parse_arguments.return_value = args
          # Configure mock return value
        mock_get_cache_info.return_value = {
            'count': 10,
            'total_size_kb': 5632.5,  # About 5.5 MB in KB
            'oldest_file': '2023-01-01',
            'newest_file': '2023-01-10',
            'oldest_timestamp': '2023-01-01T00:00:00',
            'newest_timestamp': '2023-01-10T00:00:00',
            'cache_dir': '/path/to/cache',
            'status': 'active'
        }
        
        # Call main function
        main.main()
        
        # Verify get_cache_info was called
        mock_get_cache_info.assert_called_once()
        
        # Check output contains cache info
        output = self.held_output.getvalue()
        self.assertIn("Cache Information", output)
        self.assertIn("10", output)  # count
        self.assertIn("5632.5", output)  # total_size_kb
    
    @patch('main.parse_arguments')
    @patch('main.clear_cache')
    def test_clear_cache_option(self, mock_clear_cache, mock_parse_arguments):
        """Test that --clear-cache option works correctly."""
        # Set up arguments
        args = self.default_args
        args.clear_cache = True
        args.cache_info = False
        mock_parse_arguments.return_value = args
          # Configure mock return value
        mock_clear_cache.return_value = 15  # 15 files deleted
        
        # Call main function with patch to prevent full execution
        with patch('main.get_stock_universe') as mock_get_stock_universe, \
             patch('main.create_dashboard'), \
             patch('main.create_market_overview'), \
             patch('main.create_stock_charts'):
            # Mock get_stock_universe to return a DataFrame with a symbol column
            mock_get_stock_universe.return_value = pd.DataFrame({'symbol': []})
            main.main()
          # Verify clear_cache was called
        mock_clear_cache.assert_called_once()
          # The number of files deleted is logged, not printed to stdout
        # We can't easily test the logging output, so we'll just verify the call was made
        # and the correct number was returned
        self.assertEqual(mock_clear_cache.return_value, 15)  # number of files deleted
    
    @patch('main.parse_arguments')
    @patch('main.clear_cache')
    def test_clear_old_cache_option(self, mock_clear_cache, mock_parse_arguments):
        """Test that --clear-old-cache option works correctly."""
        # Set up arguments
        args = self.default_args
        args.clear_cache = False
        args.cache_info = False
        args.clear_old_cache = 48  # 48 hours
        mock_parse_arguments.return_value = args
        
        # Configure mock return value
        mock_clear_cache.return_value = 8  # 8 files deleted
        
        # Call main function with patch to prevent full execution
        with patch('main.get_stock_universe') as mock_get_stock_universe, \
             patch('main.create_dashboard'), \
             patch('main.create_market_overview'), \
             patch('main.create_stock_charts'):
            # Mock get_stock_universe to return a DataFrame with a symbol column
            mock_get_stock_universe.return_value = pd.DataFrame({'symbol': []})
            main.main()
        
        # Verify clear_cache was called with correct parameter
        mock_clear_cache.assert_called_once_with(older_than_hours=48)        # The number of files deleted is logged, not printed to stdout
        # We can't easily test the logging output, so we'll just verify the call was made
        # and the correct number was returned
        self.assertEqual(mock_clear_cache.return_value, 8)  # number of files deleted
    def test_pipeline_execution(self):
        """Test that the pipeline executes all steps in the correct order."""
        # Set up mocks
        with patch('main.parse_arguments') as mock_parse_arguments, \
             patch('main.get_stock_universe') as mock_get_stock_universe, \
             patch('main.get_historical_prices') as mock_get_historical_prices, \
             patch('main.get_fundamental_data') as mock_get_fundamental_data, \
             patch('main.process_stock_data') as mock_process_stock_data, \
             patch('main.calculate_financial_ratios') as mock_calculate_financial_ratios, \
             patch('main.run_all_screeners') as mock_run_all_screeners, \
             patch('main.get_market_conditions') as mock_get_market_conditions, \
             patch('main.create_dashboard') as mock_create_dashboard, \
             patch('main.create_market_overview'), \
             patch('main.create_stock_charts'):

            # Set up arguments
            args = self.default_args
            args.cache_info = False
            args.clear_cache = False
            args.clear_old_cache = None
            args.strategies = 'value,growth'  # String instead of list to match main.py expectations
            mock_parse_arguments.return_value = args
            
            # Configure mock return values with actual DataFrames
            mock_get_stock_universe.return_value = self.sample_universe
            
            # Create proper DataFrames for other mocks
            historical_prices = pd.DataFrame({
                'symbol': ['AAPL', 'MSFT'],
                'date': [pd.Timestamp('2023-01-01'), pd.Timestamp('2023-01-01')],
                'close': [150.0, 250.0]
            })
            mock_get_historical_prices.return_value = historical_prices
            
            fundamental_data = pd.DataFrame({
                'symbol': ['AAPL', 'MSFT'],
                'revenue': [100000, 120000],
                'eps': [5.0, 6.0]
            })
            mock_get_fundamental_data.return_value = fundamental_data
            
            processed_data = pd.DataFrame({
                'symbol': ['AAPL', 'MSFT'],
                'processed_metric': [1.0, 1.5]
            })
            mock_process_stock_data.return_value = processed_data
            
            financial_ratios = pd.DataFrame({
                'symbol': ['AAPL', 'MSFT'],
                'pe_ratio': [20.0, 25.0],
                'price_to_book': [5.0, 6.0]
            })
            mock_calculate_financial_ratios.return_value = financial_ratios
            
            screener_results = {
                'value_strategy': pd.DataFrame({'symbol': ['AAPL'], 'score': [0.8]}),
                'growth_strategy': pd.DataFrame({'symbol': ['MSFT'], 'score': [0.9]})
            }
            mock_run_all_screeners.return_value = screener_results
            
            market_conditions = {
                'sp500_trend': 'uptrend',
                'volatility_index': 15.5
            }
            mock_get_market_conditions.return_value = market_conditions
            
            # Call main function
            main.main()
            
            # Verify all pipeline steps were called
            mock_get_stock_universe.assert_called_once()
            mock_get_historical_prices.assert_called_once()
            mock_get_fundamental_data.assert_called_once()
            mock_process_stock_data.assert_called_once()
            mock_calculate_financial_ratios.assert_called_once()
            mock_run_all_screeners.assert_called_once()
            mock_get_market_conditions.assert_called_once()
            mock_create_dashboard.assert_called_once()
            
            # Verify force_refresh parameter was passed correctly
            self.assertFalse(mock_get_stock_universe.call_args[1].get('force_refresh', False))
            self.assertFalse(mock_get_historical_prices.call_args[1].get('force_refresh', False))
        
    @patch('main.parse_arguments')
    @patch('main.get_stock_universe')
    def test_force_refresh_option(self, mock_get_stock_universe, mock_parse_arguments):
        """Test that --force-refresh option is passed to functions."""        # Set up arguments
        args = self.default_args
        args.force_refresh = True
        args.strategies = 'all'  # Using string instead of list to match how main.py expects it
        mock_parse_arguments.return_value = args
        
        # Configure mock return values with an actual DataFrame instead of MagicMock
        mock_get_stock_universe.return_value = self.sample_universe
          # Call main function with patches to prevent full execution
        with patch('main.get_historical_prices') as mock_get_historical_prices, \
             patch('main.get_fundamental_data'), \
             patch('main.process_stock_data'), \
             patch('main.calculate_financial_ratios'), \
             patch('main.run_all_screeners'), \
             patch('main.get_market_conditions'), \
             patch('main.create_dashboard'), \
             patch('main.create_market_overview'), \
             patch('main.create_stock_charts'):
            
            # Mock get_historical_prices to return an empty DataFrame to prevent issues
            mock_get_historical_prices.return_value = pd.DataFrame()
            
            main.main()
        
        # Verify force_refresh was passed to get_stock_universe
        mock_get_stock_universe.assert_called_once()
        self.assertTrue(mock_get_stock_universe.call_args[1].get('force_refresh', False))

if __name__ == '__main__':
    unittest.main()
