"""
Unit tests for config.py
"""

import unittest
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestConfig(unittest.TestCase):
    """Tests for config.py module."""
    
    @patch('os.getenv')
    @patch('dotenv.load_dotenv')
    def test_load_environment_variables(self, mock_load_dotenv, mock_getenv):
        """Test that environment variables are loaded correctly."""
        # Set up mock return values
        mock_getenv.side_effect = lambda key: {
            'ALPHA_VANTAGE_API_KEY': 'test_alpha_key',
            'FINNHUB_API_KEY': 'test_finnhub_key'
        }.get(key)
        
        # Import config module (which will execute the module code)
        # We need to reload to ensure our mocks are used
        import importlib
        import config
        importlib.reload(config)
        
        # Verify dotenv was called
        mock_load_dotenv.assert_called_once()
        
        # Verify environment variables were loaded
        self.assertEqual(config.ALPHA_VANTAGE_API_KEY, 'test_alpha_key')
        self.assertEqual(config.FINNHUB_API_KEY, 'test_finnhub_key')
    
    def test_screening_thresholds(self):
        """Test that screening thresholds have valid values."""
        import config
        thresholds = config.ScreeningThresholds
        
        # Verify some key threshold values
        self.assertLessEqual(thresholds.MAX_PRICE_TO_BOOK_RATIO, 5.0)  # Reasonable upper limit
        self.assertGreater(thresholds.MAX_PE_RATIO, 0)  # Should be positive
        self.assertGreaterEqual(thresholds.MIN_PERCENT_OFF_52_WEEK_LOW, 0)
        self.assertLessEqual(thresholds.MAX_PERCENT_OFF_52_WEEK_LOW, 100)
        self.assertGreater(thresholds.MIN_CASH_RUNWAY_MONTHS, 0)
    
    def test_directory_settings(self):
        """Test that directory settings are defined."""
        import config
        
        # Check that directory paths are defined
        self.assertTrue(hasattr(config, 'DATA_DIR'))
        self.assertTrue(hasattr(config, 'RESULTS_DIR'))
        
        # Check that paths are strings
        self.assertIsInstance(config.DATA_DIR, str)
        self.assertIsInstance(config.RESULTS_DIR, str)

if __name__ == '__main__':
    unittest.main()
