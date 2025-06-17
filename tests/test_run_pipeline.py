"""
Unit tests for run_pipeline.py
"""

import unittest
import sys
from io import StringIO
from unittest.mock import patch, MagicMock, call

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import run_pipeline

class TestRunPipeline(unittest.TestCase):
    """Tests for run_pipeline.py functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Capture stdout
        self.held_output = StringIO()
        self.old_stdout = sys.stdout
        sys.stdout = self.held_output
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore stdout
        sys.stdout = self.old_stdout
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('subprocess.run')
    def test_quick_scan_option(self, mock_subprocess_run, mock_parse_args):
        """Test that --quick option sets up correct command."""
        # Set up mock arguments
        args = MagicMock()
        args.quick = True
        args.full = False
        args.value = False
        args.output = './test_output'
        args.cache_info = False
        args.clear_cache = False
        args.force_refresh = False
        args.clear_old_cache = None
        mock_parse_args.return_value = args
        
        # Run the main function
        run_pipeline.main()
        
        # Verify subprocess.run was called with correct command
        mock_subprocess_run.assert_called_once()
        cmd = mock_subprocess_run.call_args[0][0]
        self.assertEqual(cmd[0:2], ['python', 'main.py'])
        self.assertIn('--universe', cmd)
        self.assertIn('--output', cmd)
        self.assertIn('./test_output', cmd)
        
        # Check that "Running quick scan..." was printed
        output = self.held_output.getvalue()
        self.assertIn("Running quick scan...", output)
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('subprocess.run')
    def test_full_scan_option(self, mock_subprocess_run, mock_parse_args):
        """Test that --full option sets up correct command."""
        # Set up mock arguments
        args = MagicMock()
        args.quick = False
        args.full = True
        args.value = False
        args.output = './test_output'
        args.cache_info = False
        args.clear_cache = False
        args.force_refresh = False
        args.clear_old_cache = None
        mock_parse_args.return_value = args
        
        # Run the main function
        run_pipeline.main()
        
        # Verify subprocess.run was called with correct command
        mock_subprocess_run.assert_called_once()
        cmd = mock_subprocess_run.call_args[0][0]
        self.assertEqual(cmd[0:2], ['python', 'main.py'])
        self.assertIn('--output', cmd)
        self.assertIn('./test_output', cmd)
          # Check that "Running full comprehensive scan..." was printed
        output = self.held_output.getvalue()
        self.assertIn("running full comprehensive scan", output.lower())
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('subprocess.run')
    def test_cache_options(self, mock_subprocess_run, mock_parse_args):
        """Test that cache options are passed correctly."""
        # Set up mock arguments
        args = MagicMock()
        args.quick = True
        args.full = False
        args.value = False
        args.output = './test_output'
        args.cache_info = True
        args.clear_cache = True
        args.force_refresh = True
        args.clear_old_cache = 48
        mock_parse_args.return_value = args
        
        # Run the main function
        run_pipeline.main()
        
        # Verify subprocess.run was called with correct command
        mock_subprocess_run.assert_called_once()
        cmd = mock_subprocess_run.call_args[0][0]
        self.assertEqual(cmd[0:2], ['python', 'main.py'])
        self.assertIn('--cache-info', cmd)
        self.assertIn('--clear-cache', cmd)
        self.assertIn('--force-refresh', cmd)
        self.assertIn('--clear-old-cache', cmd)
        self.assertIn('48', cmd)
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('subprocess.run')
    def test_value_option(self, mock_subprocess_run, mock_parse_args):
        """Test that --value option sets up correct command."""
        # Set up mock arguments
        args = MagicMock()
        args.quick = False
        args.full = False
        args.value = True
        args.output = './test_output'
        args.cache_info = False
        args.clear_cache = False
        args.force_refresh = False
        args.clear_old_cache = None
        mock_parse_args.return_value = args
        
        # Run the main function
        run_pipeline.main()
        
        # Verify subprocess.run was called with correct command
        mock_subprocess_run.assert_called_once()
        cmd = mock_subprocess_run.call_args[0][0]
        self.assertEqual(cmd[0:2], ['python', 'main.py'])
        self.assertIn('--strategies', cmd)
        
        # Check that value strategies are included
        value_strategies_idx = cmd.index('--strategies') + 1
        strategies = cmd[value_strategies_idx]
        self.assertIn('price_to_book', strategies)
        self.assertIn('pe_ratio', strategies)

if __name__ == '__main__':
    unittest.main()
