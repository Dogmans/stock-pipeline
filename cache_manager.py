"""
cache_manager.py - Caching system for API calls

This module provides functions for caching API responses to minimize
redundant network calls and improve the performance of the stock screening pipeline.
The cache uses a shelve-based persistence layer that persists between program restarts.

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
from utils.shared_persistence import cache_store

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_pipeline.log"),
        logging.StreamHandler()
    ]
)

# Set up logger
logger = logging.getLogger(__name__)

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

def _is_cache_valid(cache_key, expiry_hours=None):
    """
    Check if a cache entry is still valid based on its timestamp.
    
    Args:
        cache_key (str): Cache key
        expiry_hours (float, optional): Hours after which cache expires
            (defaults to config setting)
            
    Returns:
        bool: True if cache is valid, False otherwise
    """
    if expiry_hours is None:
        expiry_hours = config.CACHE_EXPIRY_HOURS
    
    # Check if the key exists
    if not cache_store.exists(cache_key):
        return False
    
    # Get the cache data with timestamp
    cached_data = cache_store.load(cache_key)
    
    if not cached_data or 'timestamp' not in cached_data:
        return False
        
    try:
        # Parse the timestamp
        timestamp = datetime.fromisoformat(cached_data['timestamp'])
        
        # Calculate expiration time
        expiry_time = datetime.now() - timedelta(hours=expiry_hours)
        
        # Check if the cache is still valid
        return timestamp > expiry_time
    except Exception as e:
        logger.error(f"Error checking cache validity for {cache_key}: {e}")
        return False

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
            from io import StringIO
            return pd.read_json(StringIO(obj['data']), orient='split', convert_dates=True)
    return obj

def cache_api_call(expiry_hours=None, cache_key_prefix=None):
    """
    Decorator to cache API call results using shelve-based persistence.
    
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
            
            # Check if we have a valid cached result
            if not force_refresh and _is_cache_valid(cache_key, expiry_hours):
                try:
                    logger.debug(f"Loading cached result for {func.__name__}")
                    cached_data = cache_store.load(cache_key)
                    
                    if not cached_data or 'result' not in cached_data['data']:
                        raise ValueError("Invalid cache data format")
                    
                    result = cached_data['data']['result']
                    
                    # Handle data types like DataFrames
                    if isinstance(result, dict) and '_type' in result:
                        result = _json_to_dataframe(result)
                    
                    return result
                except Exception as e:
                    logger.error(f"Error loading cache for {func.__name__}: {e}")
            
            # If no valid cache, call the original function
            logger.debug(f"Calling API function {func.__name__}")
            result = func(*args, **kwargs)
            
            # Save the result to cache
            try:
                # Prepare result for serialization
                serialized_result = result
                # Use DataFrame serialization for pandas objects
                if isinstance(result, pd.DataFrame):
                    serialized_result = _dataframe_to_json(result)
                    
                # Store in persistence layer
                cache_data = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'result': serialized_result
                }
                
                cache_store.save(cache_key, cache_data)
                logger.debug(f"Cached result for {func.__name__}")
            except Exception as e:
                logger.error(f"Error caching result for {func.__name__}: {e}")
            
            return result
        return wrapper
    return decorator

def clear_cache(older_than_hours=None):
    """
    Clear the entire cache or entries older than specified hours.
    
    Args:
        older_than_hours (float, optional): Only clear entries older than this many hours
            If None, clear all cache entries
            
    Returns:
        int: Number of cache entries deleted
    """
    try:
        if older_than_hours is None:
            # Clear all cache entries
            deleted_count = cache_store.clear_all()
        else:
            # Clear only entries older than specified hours
            deleted_count = cache_store.clear_older_than(older_than_hours)
            
        logger.info(f"Cleared {deleted_count} cache entries")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return 0

def get_cache_info():
    """
    Get information about the current cache.
    
    Returns:
        dict: Cache information including count, size, oldest, newest, etc.
    """
    try:
        # Get all cache keys
        cache_keys = cache_store.list_keys()
        
        if not cache_keys:
            return {
                'count': 0,
                'total_size_kb': 0,
                'status': 'empty'
            }
        
        # Get stats about entries
        timestamps = []
        for key in cache_keys:
            cached_data = cache_store.load(key)
            if cached_data and 'timestamp' in cached_data:
                timestamps.append((key, cached_data['timestamp']))
        
        if not timestamps:
            return {
                'count': len(cache_keys),
                'status': 'active',
                'message': 'Cannot determine timestamps',
                'storage_type': 'shelve'
            }
              # Sort by timestamp
        timestamps.sort(key=lambda x: x[1])
        
        # Get oldest and newest
        oldest_key, oldest_time = timestamps[0]
        newest_key, newest_time = timestamps[-1]
        
        # Get cache stats from diskcache
        cache_stats = cache_store.get_stats()
        
        return {
            'count': len(cache_keys),
            'total_size_kb': cache_stats.get('size', 0) / 1024,
            'oldest_key': oldest_key,
            'oldest_timestamp': oldest_time,
            'newest_key': newest_key,
            'newest_timestamp': newest_time,
            'storage_type': 'diskcache',
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
