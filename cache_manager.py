"""
cache_manager.py - Caching system for API calls

This module provides functions for caching API responses to minimize
redundant network calls and improve the performance of the stock screening pipeline.
The cache uses a file-based approach that persists between program restarts.

Functions:
    cache_api_call: Decorator function to cache API calls
    clear_cache: Function to clear the entire cache
    get_cache_info: Function to get information about the current cache
"""

import os
import json
import time
import hashlib
import functools
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

import config
from utils import setup_logging

# Set up logger
logger = setup_logging()

# Cache directory
CACHE_DIR = os.path.join(config.DATA_DIR, 'cache')

# Ensure cache directory exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

def _get_cache_key(func_name, args, kwargs):
    """
    Generate a unique cache key based on function name and arguments.
    
    Args:
        func_name (str): Name of the function being cached
        args (tuple): Positional arguments
        kwargs (dict): Keyword arguments
        
    Returns:
        str: Unique hash key for the cache
    """
    # Convert args and kwargs to a string representation
    args_str = str(args)
    kwargs_str = str(sorted(kwargs.items()))
    
    # Combine function name and arguments
    key_data = f"{func_name}:{args_str}:{kwargs_str}"
    
    # Create a hash of the key data
    hash_obj = hashlib.md5(key_data.encode())
    key = hash_obj.hexdigest()
    
    return key

def _get_cache_file_path(cache_key):
    """
    Get the file path for a cache key.
    
    Args:
        cache_key (str): Cache key
        
    Returns:
        str: Path to the cache file
    """
    return os.path.join(CACHE_DIR, f"{cache_key}.json")

def _is_cache_valid(cache_file, expiry_hours=None):
    """
    Check if a cache file is still valid based on its creation time.
    
    Args:
        cache_file (str): Path to the cache file
        expiry_hours (float, optional): Hours after which cache expires
            (defaults to config setting)
            
    Returns:
        bool: True if cache is valid, False otherwise
    """
    if expiry_hours is None:
        expiry_hours = config.CACHE_EXPIRY_HOURS
    
    # If the file doesn't exist, it's not valid
    if not os.path.exists(cache_file):
        return False
    
    # Get the file modification time
    file_mtime = os.path.getmtime(cache_file)
    file_date = datetime.fromtimestamp(file_mtime)
    
    # Calculate expiration time
    expiry_time = datetime.now() - timedelta(hours=expiry_hours)
    
    # Check if the file is still valid
    return file_date > expiry_time

def _dataframe_to_json(obj):
    """
    Custom JSON serializer that handles pandas DataFrames.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON serializable object
    """
    if isinstance(obj, pd.DataFrame):
        return {
            '_type': 'pandas.DataFrame',
            'data': obj.to_json(orient='split', date_format='iso')
        }
    return str(obj)

def _json_to_dataframe(obj):
    """
    Custom JSON deserializer that handles pandas DataFrames.
    
    Args:
        obj: JSON object to deserialize
        
    Returns:
        Deserialized object
    """
    if isinstance(obj, dict) and '_type' in obj:
        if obj['_type'] == 'pandas.DataFrame':
            return pd.read_json(obj['data'], orient='split')
    return obj

def cache_api_call(expiry_hours=None, cache_key_prefix=None):
    """
    Decorator to cache API call results to disk.
    
    Args:
        expiry_hours (float, optional): Hours after which cache expires
            (defaults to config setting)
        cache_key_prefix (str, optional): Prefix for the cache key
        
    Returns:
        function: Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if force_refresh is provided and remove it from kwargs
            force_refresh = kwargs.pop('force_refresh', False)
            
            # Generate a cache key
            prefix = cache_key_prefix or func.__name__
            cache_key = _get_cache_key(prefix, args, kwargs)
            cache_file = _get_cache_file_path(cache_key)
            
            # Check if we have a valid cached result
            if not force_refresh and _is_cache_valid(cache_file, expiry_hours):
                try:
                    logger.debug(f"Loading cached result for {func.__name__}")
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    
                    # Handle data types like DataFrames
                    if isinstance(cached_data['result'], dict) and '_type' in cached_data['result']:
                        cached_data['result'] = _json_to_dataframe(cached_data['result'])
                    
                    return cached_data['result']
                except Exception as e:
                    logger.error(f"Error loading cache for {func.__name__}: {e}")
            
            # If no valid cache, call the original function
            logger.debug(f"Calling API function {func.__name__}")
            result = func(*args, **kwargs)
            
            # Save the result to cache
            try:
                with open(cache_file, 'w') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs),
                        'result': result
                    }, f, default=_dataframe_to_json)
                logger.debug(f"Cached result for {func.__name__}")
            except Exception as e:
                logger.error(f"Error caching result for {func.__name__}: {e}")
            
            return result
        return wrapper
    return decorator

def clear_cache(older_than_hours=None):
    """
    Clear the entire cache or files older than specified hours.
    
    Args:
        older_than_hours (float, optional): Only clear files older than this many hours
            If None, clear all cache files
            
    Returns:
        int: Number of cache files deleted
    """
    files_deleted = 0
    
    try:
        for cache_file in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, cache_file)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            # If older_than_hours is specified, check file age
            if older_than_hours is not None:
                file_mtime = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(file_mtime)
                cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                
                if file_date > cutoff_time:
                    continue
            
            # Delete the file
            os.remove(file_path)
            files_deleted += 1
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
    
    logger.info(f"Cleared {files_deleted} cache files")
    return files_deleted

def get_cache_info():
    """
    Get information about the current cache.
    
    Returns:
        dict: Cache information including count, size, oldest, newest, etc.
    """
    try:
        # Get all cache files
        cache_files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) 
                      if os.path.isfile(os.path.join(CACHE_DIR, f))]
        
        if not cache_files:
            return {
                'count': 0,
                'total_size_kb': 0,
                'status': 'empty'
            }
        
        # Get file stats
        file_stats = []
        total_size = 0
        
        for file_path in cache_files:
            size = os.path.getsize(file_path)
            mtime = os.path.getmtime(file_path)
            file_stats.append((file_path, size, mtime))
            total_size += size
        
        # Sort by modification time
        file_stats.sort(key=lambda x: x[2])
        
        # Get oldest and newest
        oldest_file, _, oldest_time = file_stats[0]
        newest_file, _, newest_time = file_stats[-1]
        
        return {
            'count': len(cache_files),
            'total_size_kb': total_size / 1024,
            'oldest_file': os.path.basename(oldest_file),
            'oldest_timestamp': datetime.fromtimestamp(oldest_time).isoformat(),
            'newest_file': os.path.basename(newest_file),
            'newest_timestamp': datetime.fromtimestamp(newest_time).isoformat(),
            'cache_dir': CACHE_DIR,
            'status': 'active'
        }
    
    except Exception as e:
        logger.error(f"Error getting cache info: {e}")
        return {
            'error': str(e),
            'status': 'error'
        }

if __name__ == "__main__":
    # Test the cache system
    print("Cache Manager - Test Mode")
    
    # Create some test data
    @cache_api_call()
    def test_function(param1, param2=None):
        print(f"Running actual function with {param1}, {param2}")
        return {
            "data": f"Result for {param1}, {param2}",
            "timestamp": time.time()
        }
    
    # Run the test function
    print("First call (should hit API):")
    result1 = test_function("test", param2="value")
    print(f"Result: {result1}")
    
    print("\nSecond call (should use cache):")
    result2 = test_function("test", param2="value")
    print(f"Result: {result2}")
    
    print("\nThird call with force_refresh (should hit API):")
    result3 = test_function("test", param2="value", force_refresh=True)
    print(f"Result: {result3}")
    
    print("\nCache info:")
    print(get_cache_info())
