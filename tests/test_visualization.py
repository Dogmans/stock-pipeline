"""
Unit tests for visualization.py
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, ANY

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestVisualization(unittest.TestCase):
    """Tests for visualization module functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample screening data
        self.sample_data = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META'],
            'company_name': ['Apple Inc', 'Microsoft Corp', 'Alphabet Inc', 'Amazon.com Inc', 'Meta Platforms Inc'],
            'sector': ['Technology', 'Technology', 'Technology', 'Consumer Cyclical', 'Communication Services'],
            'market_cap': [2500000000000, 2000000000000, 1500000000000, 1000000000000, 800000000000],
            'price': [150.25, 300.50, 140.75, 100.25, 200.50],
            'pe_ratio': [25.5, 30.2, 22.1, 40.5, 15.3],
            'pct_off_high': [10.5, 5.2, 15.3, 25.1, 30.5],
            'pct_above_low': [25.3, 30.1, 10.2, 5.3, 15.2],
            'ytd_return': [-5.2, 10.3, -2.5, -15.3, 8.2]
        })
        
        # Sample market data
        self.market_data = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=30),
            'close': np.random.normal(loc=4500, scale=100, size=30),
            'volume': np.random.randint(1000000, 9000000, size=30)
        })
    
    @patch('visualization.px.scatter')
    def test_plot_52_week_lows(self, mock_scatter):
        """Test that 52-week low visualization is created correctly."""
        # Import visualization after mocking
        import visualization
        
        # Create mock figure
        mock_fig = MagicMock()
        mock_scatter.return_value = mock_fig
        mock_fig.update_layout.return_value = mock_fig
        
        # Call function with sample data
        result = visualization.plot_52_week_lows(self.sample_data)
        
        # Verify scatter was called with correct arguments
        mock_scatter.assert_called_once()
        call_args = mock_scatter.call_args[1]
        self.assertEqual(call_args['x'], 'pct_above_low')
        self.assertEqual(call_args['y'], 'pct_off_high')
        self.assertEqual(call_args['color'], 'sector')
        self.assertEqual(call_args['size'], 'market_cap')
        
        # Verify layout was updated
        mock_fig.update_layout.assert_called_once()
        
        # Verify result is the mock figure
        self.assertEqual(result, mock_fig)
    
    @patch('visualization.px.scatter')
    def test_plot_52_week_lows_empty_data(self, mock_scatter):
        """Test 52-week low visualization with empty data."""
        # Import visualization after mocking
        import visualization
        
        # Call function with empty data
        result = visualization.plot_52_week_lows(pd.DataFrame())
        
        # Verify scatter was not called
        mock_scatter.assert_not_called()
        
        # Verify result is None for empty data
        self.assertIsNone(result)
    
    @patch('visualization.make_subplots')
    @patch('visualization.go.Figure')
    def test_create_market_overview(self, mock_figure, mock_subplots):
        """Test market overview visualization."""
        # Import visualization after mocking
        import visualization
        
        # Set up mock figures
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig
        mock_fig.add_trace.return_value = None
        mock_fig.update_layout.return_value = mock_fig
        
        # Create sample market index data
        market_indexes = {
            'SPY': self.market_data,
            'QQQ': self.market_data
        }
        
        # Mock plt to avoid actual plotting
        with patch('visualization.plt'):
            result = visualization.create_market_overview(market_indexes)
        
        # Verify subplots were created
        mock_subplots.assert_called_once()
        
        # Verify traces were added
        self.assertTrue(mock_fig.add_trace.called)
        
        # Verify layout was updated
        mock_fig.update_layout.assert_called_once()
        
        # Verify result is the mock figure
        self.assertEqual(result, mock_fig)

# Add more tests for other visualization functions as needed

if __name__ == '__main__':
    unittest.main()
