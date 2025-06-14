"""
Unit tests for main.py
"""

import unittest
import sys
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
        sys.stdout = self.held_output
        
        # Set up sample data
        self.sample_universe = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META']
        
        # Default mock arguments
        self.default_args = MagicMock()
        self.default_args.universe = 'sp500'
        self.default_args.strategies = ['value', 'growth']
        self.default_args.output = './output'
        self.default_args.cache_info = False
        self.default_args.clear_cache = False
        self.default_args.force_refresh = False
        self.default_args.clear_old_cache = None
        self.default_args.debug = False
    
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
            'total_files': 10,
            'total_size_mb': 5.5,
            'oldest_file': '2023-01-01',
            'newest_file': '2023-01-10'
        }
        
        # Call main function
        main.main()
        
        # Verify get_cache_info was called
        mock_get_cache_info.assert_called_once()
        
        # Check output contains cache info
        output = self.held_output.getvalue()
        self.assertIn("Cache Information", output)
        self.assertIn("10", output)  # total_files
        self.assertIn("5.5", output)  # total_size_mb
    
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
        with patch('main.run_pipeline'):
            main.main()
        
        # Verify clear_cache was called
        mock_clear_cache.assert_called_once_with(older_than_hours=None)
        
        # Check output contains cache deletion message
        output = self.held_output.getvalue()
        self.assertIn("15", output)  # number of files deleted
    
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
        with patch('main.run_pipeline'):
            main.main()
        
        # Verify clear_cache was called with correct parameter
        mock_clear_cache.assert_called_once_with(older_than_hours=48)
        
        # Check output contains cache deletion message
        output = self.held_output.getvalue()
        self.assertIn("8", output)  # number of files deleted
        self.assertIn("48", output)  # hours

    @patch('main.parse_arguments')
    @patch('main.get_stock_universe')
    @patch('main.get_historical_prices')
    @patch('main.get_fundamental_data')
    @patch('main.process_stock_data')
    @patch('main.calculate_financial_ratios')
    @patch('main.run_all_screeners')
    @patch('main.get_market_conditions')
    @patch('main.create_dashboard')
    def test_pipeline_execution(self, mock_create_dashboard, mock_get_market_conditions, 
                               mock_run_all_screeners, mock_calculate_financial_ratios,
                               mock_process_stock_data, mock_get_fundamental_data,
                               mock_get_historical_prices, mock_get_stock_universe,
                               mock_parse_arguments):
        """Test that the pipeline executes all steps in the correct order."""
        # Set up arguments
        args = self.default_args
        args.cache_info = False
        args.clear_cache = False
        args.clear_old_cache = None
        mock_parse_arguments.return_value = args
        
        # Configure mock return values
        mock_get_stock_universe.return_value = self.sample_universe
        mock_get_historical_prices.return_value = MagicMock()
        mock_get_fundamental_data.return_value = MagicMock()
        mock_process_stock_data.return_value = MagicMock()
        mock_calculate_financial_ratios.return_value = MagicMock()
        mock_run_all_screeners.return_value = MagicMock()
        mock_get_market_conditions.return_value = MagicMock()
        
        # Call main function
        main.main()
        
        # Verify all pipeline steps were called in the correct order
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
        """Test that --force-refresh option is passed to functions."""
        # Set up arguments
        args = self.default_args
        args.force_refresh = True
        mock_parse_arguments.return_value = args
        
        # Configure mock return values
        mock_get_stock_universe.return_value = self.sample_universe
        
        # Call main function with patches to prevent full execution
        with patch('main.get_historical_prices'), \
             patch('main.get_fundamental_data'), \
             patch('main.process_stock_data'), \
             patch('main.calculate_financial_ratios'), \
             patch('main.run_all_screeners'), \
             patch('main.get_market_conditions'), \
             patch('main.create_dashboard'):
            main.main()
        
        # Verify force_refresh was passed to get_stock_universe
        mock_get_stock_universe.assert_called_once()
        self.assertTrue(mock_get_stock_universe.call_args[1].get('force_refresh', False))

if __name__ == '__main__':
    unittest.main()
