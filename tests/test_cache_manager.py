"""
Unit tests for cache_manager.py
"""

import unittest
import os
import json
import tempfile
import shutil
import time
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from cache_manager import (
    _get_cache_key, _is_cache_valid, 
    cache_api_call, clear_cache, get_cache_info,
    _dataframe_to_json, _json_to_dataframe
)
from utils.shared_persistence import cache_store

class TestCacheManager(unittest.TestCase):
    """Tests for the cache manager module."""
      def setUp(self):
        """Set up test environment."""
        # Create temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        # Store original cache directory
        self.original_cache_dir = config.DATA_DIR
        # Patch config to use temporary directory
        self.cache_dir_patcher = patch('cache_manager.CACHE_DIR', self.temp_dir)
        self.cache_dir_patcher.start()
        
        # Mock the cache_store for tests
        self.mock_cache_store = MagicMock()
        self.cache_store_patcher = patch('cache_manager.cache_store', self.mock_cache_store)
        self.cache_store_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop patches
        self.cache_dir_patcher.stop()
        self.cache_store_patcher.stop()
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)

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

    def test_get_cache_file_path(self):
        """Test generating cache file path."""
        cache_key = "test_cache_key"
        file_path = _get_cache_file_path(cache_key)
        expected_path = os.path.join(self.temp_dir, f"{cache_key}.json")
        self.assertEqual(file_path, expected_path)

    def test_is_cache_valid(self):
        """Test cache validation based on time."""
        # Create a test cache file
        cache_file = os.path.join(self.temp_dir, "test_cache.json")
        with open(cache_file, 'w') as f:
            f.write('{"test": "data"}')
        
        # Test with valid cache (file just created)
        self.assertTrue(_is_cache_valid(cache_file, 24))
        
        # Test with invalid cache (file too old)
        # Mock os.path.getmtime to return a time in the past
        future_time = time.time() - 25 * 3600  # 25 hours ago
        with patch('os.path.getmtime', return_value=future_time):
            self.assertFalse(_is_cache_valid(cache_file, 24))
        
        # Test with non-existent file
        self.assertFalse(_is_cache_valid("nonexistent_file.json", 24))
    
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

    def test_cache_api_call_decorator(self):
        """Test the cache_api_call decorator."""
        # Create a mock function that counts calls
        mock_func = MagicMock(return_value={'data': 'test'})
        mock_func.__name__ = 'mock_func'
        
        # Apply decorator
        decorated_func = cache_api_call(expiry_hours=24)(mock_func)
        
        # First call should hit the function
        result1 = decorated_func('arg1', kwarg1='value1')
        self.assertEqual(result1, {'data': 'test'})
        mock_func.assert_called_once()
        
        # Second call should use cache
        result2 = decorated_func('arg1', kwarg1='value1')
        self.assertEqual(result2, {'data': 'test'})
        # Should still be called only once (cache hit)
        self.assertEqual(mock_func.call_count, 1)
        
        # Call with force_refresh should hit the function again
        result3 = decorated_func('arg1', kwarg1='value1', force_refresh=True)
        self.assertEqual(result3, {'data': 'test'})
        self.assertEqual(mock_func.call_count, 2)
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Create some test cache files
        for i in range(5):
            file_path = os.path.join(self.temp_dir, f"cache_file_{i}.json")
            with open(file_path, 'w') as f:
                f.write('{"test": "data"}')
        
        # Verify files exist
        self.assertEqual(len(os.listdir(self.temp_dir)), 5)
        
        # Clear cache
        files_deleted = clear_cache()
        self.assertEqual(files_deleted, 5)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
    
    def test_clear_cache_older_than(self):
        """Test clearing cache files older than specified time."""
        # Create some test cache files with different timestamps
        now = time.time()
        
        # Create 3 new files
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"new_file_{i}.json")
            with open(file_path, 'w') as f:
                f.write('{"test": "data"}')
        
        # Create 2 old files
        for i in range(2):
            file_path = os.path.join(self.temp_dir, f"old_file_{i}.json")
            with open(file_path, 'w') as f:
                f.write('{"test": "data"}')
            # Set modification time to 2 days ago
            os.utime(file_path, (now, now - 48 * 3600))
        
        # Verify all files exist
        self.assertEqual(len(os.listdir(self.temp_dir)), 5)
        
        # Clear files older than 24 hours
        with patch('os.path.getmtime', side_effect=lambda f: now if 'new' in f else now - 48 * 3600):
            files_deleted = clear_cache(older_than_hours=24)
            self.assertEqual(files_deleted, 2)
            # Only new files should remain
            self.assertEqual(len(os.listdir(self.temp_dir)), 3)
    
    def test_get_cache_info(self):
        """Test getting cache info."""
        # Create some test cache files
        now = time.time()
        
        # Create a newer file
        newer_file = os.path.join(self.temp_dir, "newer_file.json")
        with open(newer_file, 'w') as f:
            f.write('{"test": "data"}')
        
        # Create an older file
        older_file = os.path.join(self.temp_dir, "older_file.json")
        with open(older_file, 'w') as f:
            f.write('{"test": "data"}')
        # Set modification time to 1 day ago
        os.utime(older_file, (now, now - 24 * 3600))
        
        # Mock os.path getmtime and getsize
        with patch('os.path.getmtime', side_effect=lambda f: now if 'newer' in f else now - 24 * 3600):
            with patch('os.path.getsize', return_value=100):
                info = get_cache_info()
                
                self.assertEqual(info['count'], 2)
                self.assertEqual(info['total_size_kb'], 200 / 1024)
                self.assertEqual(info['oldest_file'], "older_file.json")
                self.assertEqual(info['newest_file'], "newer_file.json")
                self.assertEqual(info['status'], "active")

if __name__ == '__main__':
    unittest.main()
