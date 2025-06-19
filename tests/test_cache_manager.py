"""
Unit tests for cache_manager.py

These tests directly use the real cache implementation with diskcache
instead of mocks and temporary directories.
"""

import unittest
import time
import pandas as pd
from datetime import datetime, timedelta
import json
import uuid

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from cache_manager import (
    _get_cache_key,
    cache_api_call, clear_cache, get_cache_info,
    _dataframe_to_json, _json_to_dataframe,
    _is_cache_valid
)
from utils.shared_persistence import cache_store

class TestCacheManager(unittest.TestCase):
    """Tests for the cache manager module."""
    
    def setUp(self):
        """Set up test environment with real cache."""
        # We'll use an isolated test area in the real cache for our tests
        self.test_prefix = f"test_cache_manager_{uuid.uuid4().hex}_"
        self.test_keys = []
        
    def tearDown(self):
        """Clean up after tests by removing test keys."""
        # Clean up any keys we created
        for key in self.test_keys:
            cache_store.delete(key)
            
    def test_get_cache_key(self):
        """Test generating a cache key."""
        key1 = _get_cache_key('test_func', ('arg1', 'arg2'), {'kwarg1': 'value1'})
        # Same function and args should produce same key
        key2 = _get_cache_key('test_func', ('arg1', 'arg2'), {'kwarg1': 'value1'})
        self.assertEqual(key1, key2)
        # Different function should produce different key
        key3 = _get_cache_key('other_func', ('arg1', 'arg2'), {'kwarg1': 'value1'})
        self.assertNotEqual(key1, key3)
        # Different args should produce different key
        key4 = _get_cache_key('test_func', ('arg1', 'arg3'), {'kwarg1': 'value1'})
        self.assertNotEqual(key1, key4)
        
    def test_cache_store_integration(self):
        """Test integration with the real cache_store."""
        # Generate a unique test key
        test_key = f"{self.test_prefix}integration_{int(time.time())}"
        self.test_keys.append(test_key)
        
        # Save some data to the cache
        test_data = {"message": "test data"}
        cache_store.save(test_key, test_data)
        
        # Verify we can load the data back
        loaded_data = cache_store.load(test_key)
        self.assertIsNotNone(loaded_data)
        self.assertIn('data', loaded_data)
        self.assertEqual(loaded_data['data'], test_data)
    def test_is_cache_valid(self):
        """Test cache validation based on time."""
        # Create a test entry that is current
        current_key = f"{self.test_prefix}current_{int(time.time())}"
        self.test_keys.append(current_key)
        cache_store.save(current_key, {"test": "current"})
        
        # Create a test entry that's expired (manually set timestamp)
        expired_key = f"{self.test_prefix}expired_{int(time.time())}"
        self.test_keys.append(expired_key)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache_store.save(
            expired_key, 
            {"test": "expired"}, 
            {"timestamp": old_time}  # Override the timestamp
        )
        
        # Test valid cache
        self.assertTrue(_is_cache_valid(current_key, 24))
        
        # Test expired cache
        self.assertFalse(_is_cache_valid(expired_key, 24))
        
        # Test non-existent cache key
        self.assertFalse(_is_cache_valid("nonexistent_key", 24))
    
    def test_dataframe_serialization(self):
        """Test serialization of pandas DataFrame."""
        # Create a test DataFrame
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['a', 'b', 'c'],
            'C': ['2022-01-01', '2022-01-02', '2022-01-03']
        })
        
        # Serialize
        serialized = _dataframe_to_json(df)
        self.assertEqual(serialized.get('_type'), 'pandas.DataFrame')
        self.assertTrue(isinstance(serialized.get('data'), str))
        
        # Deserialize
        deserialized = _json_to_dataframe(serialized)
        pd.testing.assert_frame_equal(df, deserialized)
          # Test with non-DataFrame
        regular_obj = {'key': 'value'}
        self.assertEqual(_dataframe_to_json(regular_obj), str(regular_obj))
        self.assertEqual(_json_to_dataframe(regular_obj), regular_obj)
        
    def test_cache_api_call_decorator_real(self):
        """Test the cache_api_call decorator with a real function."""
        call_count = 0
        
        # Define a test function to be decorated
        @cache_api_call(expiry_hours=1, cache_key_prefix=self.test_prefix)
        def test_func(param, kwparam=None):
            nonlocal call_count
            call_count += 1
            return {
                "param": param,
                "kwparam": kwparam,
                "call_count": call_count
            }
        
        # Add key to cleanup list - extract it by calling the function and seeing the key
        key = _get_cache_key(self.test_prefix, ("test_value",), {"kwparam": "test_kwparam"})
        self.test_keys.append(key)
        
        # First call should execute the function
        result1 = test_func("test_value", kwparam="test_kwparam")
        self.assertEqual(result1["call_count"], 1)
        self.assertEqual(result1["param"], "test_value")
        
        # Second call should use the cache
        result2 = test_func("test_value", kwparam="test_kwparam")
        self.assertEqual(result2["call_count"], 1)  # Still 1, not incremented
        
        # Call with force_refresh should execute the function again
        result3 = test_func("test_value", kwparam="test_kwparam", force_refresh=True)
        self.assertEqual(result3["call_count"], 2)  # Should increment to 2
        
        # Different parameters should create different cache entry
        new_key = _get_cache_key(self.test_prefix, ("different",), {"kwparam": "different"})
        self.test_keys.append(new_key)
        result4 = test_func("different", kwparam="different")
        self.assertEqual(result4["call_count"], 3)  # Should increment to 3
    def test_clear_and_get_cache(self):
        """Test clearing the cache and getting cache info with real cache."""
        # Add several test entries to the cache
        for i in range(5):
            key = f"{self.test_prefix}clear_test_{i}"
            self.test_keys.append(key)
            cache_store.save(key, {"test_data": f"value_{i}"})
        
        # Get initial cache info
        before_info = get_cache_info()
        initial_count = before_info['count']
        
        # First create a snapshot of existing keys to avoid clearing real cache
        real_keys = [key for key in cache_store.list_keys() 
                     if key.startswith(self.test_prefix)]
        
        # Test partial clear with older_than
        # First add a test entry with an old timestamp
        old_key = f"{self.test_prefix}old_entry"
        self.test_keys.append(old_key)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache_store.save(old_key, {"test": "old_data"}, {"timestamp": old_time})
        
        # Clear entries older than 24 hours (should only clear our old entry)
        deleted = clear_cache(older_than_hours=24)
        self.assertEqual(deleted, 1)  # Our single old entry
        
        # Test that our old entry is gone but newer ones remain
        self.assertFalse(cache_store.exists(old_key))
        
        # Now clear all our test entries
        # We'll only clear our test keys to avoid disrupting real cache
        for key in self.test_keys:
            cache_store.delete(key)
        
        # Verify they're gone
        for key in self.test_keys:
            self.assertFalse(cache_store.exists(key))
    
    def test_get_cache_info(self):
        """Test getting cache info from the real cache."""
        # Add multiple test entries to the cache
        for i in range(5):
            key = f"{self.test_prefix}info_test_{i}"
            self.test_keys.append(key)
            cache_store.save(key, {"test_data": f"value_{i}"})
        
        # Get cache info
        info = get_cache_info()
        
        # Basic validations
        self.assertIsInstance(info, dict)
        self.assertIn('count', info)
        self.assertIn('total_size_kb', info)
        self.assertIn('storage_type', info)
        self.assertIn('status', info)
        
        # The total count should be at least our 5 test entries
        self.assertGreaterEqual(info['count'], 5)
        
        # Storage type should be diskcache
        self.assertEqual(info['storage_type'], 'diskcache')
        
        # Status should be active
        self.assertEqual(info['status'], 'active')

if __name__ == '__main__':
    unittest.main()
