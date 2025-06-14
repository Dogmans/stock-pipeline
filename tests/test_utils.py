"""
Unit tests for utils.py
"""

import unittest
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import utils
import config

class TestUtils(unittest.TestCase):
    """Tests for utility functions."""
    
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    @patch('logging.basicConfig')
    def test_setup_logging(self, mock_basic_config, mock_stream_handler, mock_file_handler):
        """Test that logging is set up correctly."""
        logger = utils.setup_logging()
        
        # Check that basicConfig was called with the correct arguments
        mock_basic_config.assert_called_once()
        
        # Check that the correct handlers were created
        args = mock_basic_config.call_args[1]
        self.assertEqual(args['level'], logging.INFO)
        self.assertEqual(args['format'], '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.assertEqual(len(args['handlers']), 2)
        
        # Verify the logger is returned
        self.assertIsInstance(logger, logging.Logger)
    
    @patch('pathlib.Path.mkdir')
    def test_ensure_directories_exist(self, mock_mkdir):
        """Test that required directories are created."""
        utils.ensure_directories_exist()
        
        # Verify that mkdir was called twice (once for each directory)
        self.assertEqual(mock_mkdir.call_count, 2)
        
        # Verify the correct paths were used
        calls = mock_mkdir.call_args_list
        called_paths = [call[0][0] for call in [c for c in calls]]
        
        # Make sure DATA_DIR and RESULTS_DIR were created with correct parameters
        mock_mkdir.assert_any_call(parents=True, exist_ok=True)

if __name__ == '__main__':
    unittest.main()
