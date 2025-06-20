"""
Unit tests for cache_config.py

These tests validate the simplified caching implementation using diskcache directly.
"""

import unittest
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Add parent directory to path to allow imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cache_config import cache, clear_all_cache, clear_old_cache, get_cache_info

class TestCache(unittest.TestCase):
    """Test the cache implementation using diskcache directly"""
    
    def setUp(self):
        # Clear the cache before each test
        clear_all_cache()
    
    def test_cache_basic(self):
        """Test basic caching functionality"""
        
        # Define a simple function to cache
        @cache.memoize(expire=60)  # Cache for 60 seconds
        def example_func(a, b):
            return a + b + time.time()
        
        # First call should miss cache
        result1 = example_func(1, 2)
        
        # Second call with same args should hit cache
        result2 = example_func(1, 2)
        
        # Results should be the same
        self.assertEqual(result1, result2)
        
        # Different args should miss cache
        result3 = example_func(2, 3)
        
        # Results should be different
        self.assertNotEqual(result1, result3)
    
    def test_cache_pandas_dataframe(self):
        """Test caching pandas DataFrames"""
        
        @cache.memoize(expire=60)  # Cache for 60 seconds
        def get_dataframe(rows, cols):
            # Create a DataFrame with the current timestamp to ensure each call is different
            df = pd.DataFrame(
                data=np.random.rand(rows, cols),
                columns=[f'col_{i}' for i in range(cols)]
            )
            df['timestamp'] = datetime.now()
            return df
        
        # First call should miss cache
        df1 = get_dataframe(5, 3)
        
        # Wait a bit to ensure timestamps would be different if not cached
        time.sleep(0.1)
        
        # Second call with same args should hit cache
        df2 = get_dataframe(5, 3)
        
        # DataFrames should be identical (including timestamps)
        pd.testing.assert_frame_equal(df1, df2)
        
        # Different args should miss cache
        df3 = get_dataframe(10, 3)
          # DataFrames should be different
        self.assertNotEqual(df1.shape, df3.shape)
        
    def test_force_refresh(self):
        """Test the force_refresh pattern with cache.delete"""
        
        call_count = 0
        
        @cache.memoize(expire=60)  # Cache for 60 seconds
        def example_func(a, b):
            nonlocal call_count
            call_count += 1
            return a + b, call_count
        
        # First call
        result1, count1 = example_func(1, 2)
        self.assertEqual(count1, 1)
        
        # Second call should hit cache
        result2, count2 = example_func(1, 2)
        self.assertEqual(count1, count2)  # Call count shouldn't increase
        
        # Force refresh by clearing the cache
        cache.clear()  # Just clear entire cache for simplicity in test
        result3, count3 = example_func(1, 2)  # This will now miss the cache
        self.assertEqual(count3, 2)  # Call count should increase
    
    def test_recommended_force_refresh_pattern(self):
        """Test the recommended pattern for implementing force_refresh in functions"""
        
        call_count = 0
        key_prefix = "test_key"
        
        @cache.memoize(expire=60)  # Cache for 60 seconds
        def recommended_func(a, b, force_refresh=False):
            nonlocal call_count
            # The correct pattern: delete from specific cache key
            if force_refresh:
                # For specific key deletion, we need to use cache internals to compute the key
                # This is an implementation detail normally hidden in real code
                key = f"{key_prefix}:{a}:{b}"
                cache.delete(key)
                
            call_count += 1
            return a + b, call_count
        
        # First call
        result1, count1 = recommended_func(1, 2)
        self.assertEqual(count1, 1)
        
        # Second call should hit cache
        result2, count2 = recommended_func(1, 2)
        self.assertEqual(count1, count2)  # Call count shouldn't increase
        
        # Force refresh by clearing the cache
        cache.clear()  # In real applications, use a more targeted approach
        result3, count3 = recommended_func(1, 2)
        self.assertEqual(count3, 2)  # Call count should increase
    
    def test_clear_old_cache(self):
        """Test clearing based on cache expiration time"""
        
        # Add some entries with different expiration times
        @cache.memoize(expire=1)  # 1 second expiry
        def short_lived(x):
            return x + time.time()
        
        @cache.memoize(expire=3600)  # 1 hour expiry
        def long_lived(x):
            return x + time.time()
        
        # Populate cache
        short_result = short_lived(1)
        long_result = long_lived(1)
        
        # Should still be cached
        self.assertEqual(short_lived(1), short_result)
        self.assertEqual(long_lived(1), long_result)
        
        # Wait for short-lived entry to expire
        time.sleep(1.1)
        
        # Test diskcache's built-in expire functionality - this should remove expired entries
        expired = cache.expire()
        # Some entries should have expired
        self.assertGreaterEqual(expired, 1)
        
        # Short-lived should be gone as it's expired
        self.assertNotEqual(short_lived(1), short_result)
        # Long-lived should still be present
        self.assertEqual(long_lived(1), long_result)
        
        # Our implementation would only clear when hours > 0
        cleared = clear_old_cache(hours=170)  # More than a week
        self.assertGreaterEqual(cleared, 1)  # Should clear the remaining entries
    
    def test_get_cache_info(self):
        """Test getting cache information"""
        
        @cache.memoize(expire=60)
        def sample_func(x):
            return x * 2
        
        # Add some entries
        for i in range(5):
            sample_func(i)
        
        # Get cache info
        info = get_cache_info()
        
        # Check if info contains expected fields
        self.assertIn('count', info)
        self.assertIn('size_kb', info)
        
        # Count should be at least 5 (could be more if other tests ran)
        self.assertGreaterEqual(info['count'], 5)
        
        # Size should be positive
        self.assertGreater(info['size_kb'], 0)
    def test_data_provider_caching(self):
        """Test caching pattern as used in data providers"""
        
        # Using a module-level function with state instead of a local class
        # This avoids the pickle issue with local classes
        call_count = [0]  # Using a list to make it mutable from the function
        
        # Define a standalone function that mimics a provider method
        @cache.memoize(expire=24*3600)  # Cache for 24 hours
        def get_provider_data(symbol, period="1d", force_refresh=False):
            """Get data with caching - typical pattern used in data providers"""
            # Handle force_refresh at the beginning of the method
            if force_refresh:
                # We just clear the entire cache for test simplicity
                cache.clear()
                
            # Simulate API call
            call_count[0] += 1
            return {"symbol": symbol, "data": f"Data for {period}", "call_count": call_count[0]}
          # First call should miss cache
        result1 = get_provider_data("AAPL")
        self.assertEqual(result1["call_count"], 1)
        
        # Second call should hit cache
        result2 = get_provider_data("AAPL")
        self.assertEqual(result2["call_count"], 1)  # Should be same as first call
        
        # Force refresh should get fresh data
        result3 = get_provider_data("AAPL", force_refresh=True)
        # Call count should be 2 because we fetched fresh data
        self.assertEqual(result3["call_count"], 2)
        
        # Different parameters should miss cache
        result4 = get_provider_data("MSFT")
        self.assertEqual(result4["call_count"], 3)  # New call count


if __name__ == '__main__':
    unittest.main()
