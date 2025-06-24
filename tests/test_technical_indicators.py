"""
Test module for technical indicators
"""

import unittest
import pandas as pd
import numpy as np
from technical_indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_technical_indicators

class TestTechnicalIndicators(unittest.TestCase):
    def setUp(self):
        # Create test price data
        dates = pd.date_range(start='2023-01-01', periods=100)
        self.test_data = pd.DataFrame({
            'open': np.random.normal(100, 5, 100),
            'high': np.random.normal(105, 5, 100),
            'low': np.random.normal(95, 5, 100),
            'close': np.random.normal(100, 5, 100),
            'volume': np.random.normal(1000000, 200000, 100)
        }, index=dates)
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        # Calculate RSI from test data
        rsi = calculate_rsi(self.test_data['close'])
        
        # Check that the result has the expected shape
        self.assertEqual(len(rsi), 100)
        
        # Check that values are within the expected range (0-100)
        self.assertTrue(all((0 <= x <= 100) for x in rsi[14:] if not np.isnan(x)))
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        # Calculate MACD from test data
        macd, signal, hist = calculate_macd(self.test_data['close'])
        
        # Check that the result has the expected shape
        self.assertEqual(len(macd), 100)
        self.assertEqual(len(signal), 100)
        self.assertEqual(len(hist), 100)
        
        # Check that MACD values are calculated after sufficient data points
        self.assertTrue(not np.isnan(macd[33]))  # After 26 + some signal periods
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation"""
        # Calculate Bollinger Bands from test data
        upper, middle, lower = calculate_bollinger_bands(self.test_data['close'])
        
        # Check that the result has the expected shape
        self.assertEqual(len(upper), 100)
        self.assertEqual(len(middle), 100)
        self.assertEqual(len(lower), 100)
        
        # Check that bands are properly ordered (upper > middle > lower)
        for i in range(25, 100):  # Check after the initial window
            if not np.isnan(upper[i]) and not np.isnan(middle[i]) and not np.isnan(lower[i]):
                self.assertTrue(upper[i] > middle[i] > lower[i])
    
    def test_calculate_technical_indicators(self):
        """Test the main technical indicators calculation function"""
        # Calculate all indicators
        df_with_indicators = calculate_technical_indicators(self.test_data)
        
        # Check that the dataframe has the expected indicators
        expected_columns = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_20', 'sma_50', 'sma_200',
            'ema_12', 'ema_26',
            'macd', 'macd_signal', 'macd_hist',
            'volume_ma', 'volume_ratio'
        ]
        for col in expected_columns:
            self.assertIn(col, df_with_indicators.columns)
        
        # Depending on TA-Lib availability, additional columns may be present
        possible_extra_columns = [
            'rsi', 'upper_band', 'middle_band', 'lower_band',
            'slowk', 'slowd', 'adx', 'atr', 'obv', 'cci'
        ]
        
        # Check that the dataframe has the same number of rows
        self.assertEqual(len(df_with_indicators), len(self.test_data))

if __name__ == '__main__':
    unittest.main()
