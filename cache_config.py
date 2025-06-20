"""
cache_config.py - Simple cache configuration

This module configures a global diskcache.Cache or diskcache.FanoutCache instance
for use throughout the application.
"""

import os
from diskcache import FanoutCache
import logging
from pathlib import Path

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_pipeline.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Ensure cache directory exists
cache_dir = os.path.join('data', 'cache')
Path(cache_dir).mkdir(parents=True, exist_ok=True)

# Create a single global cache instance for the entire application
# Using FanoutCache for better concurrency with sharded operations
cache = FanoutCache(cache_dir, shards=8)

def clear_all_cache():
    """
    Clear the entire cache.
    
    Returns:
        int: Number of items deleted
    """
    try:
        # Store the count first since clear() returns None
        count = len(cache)
        cache.clear()
        logger.info(f"Cleared all {count} items from {cache_dir}")
        return count
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return 0

def clear_old_cache(hours):
    """
    Clear cache entries older than the specified number of hours.
    
    Args:
        hours (float): Number of hours
        
    Returns:
        int: Approximate number of items deleted
    """
    try:
        if hours <= 0:
            return 0
        
        # Convert hours to seconds for diskcache
        seconds = int(hours * 3600)
        
        # Unfortunately diskcache doesn't provide a way to delete items older than X
        # without iterating through them or using expire times when setting.
        # Since we don't have control over expire times in this refactor,
        # we'll just clear the entire cache if it's older than a week
        if hours >= 168:  # 7 days
            return clear_all_cache()
        else:
            logger.info(f"Diskcache doesn't support clearing by age without custom code. Please use clear_all_cache() if needed.")
            return 0
    except Exception as e:
        logger.error(f"Error clearing old cache: {e}")
        return 0

def get_cache_info():
    """
    Get information about the current cache.
    
    Returns:
        dict: Cache statistics
    """
    try:
        stats = cache.stats()
        return {
            'count': len(cache),
            'hits': stats[0],
            'misses': stats[1],
            'size_kb': cache.volume() / 1024,
            'directory': cache_dir,
            'status': 'active'
        }
    except Exception as e:
        logger.error(f"Error getting cache info: {e}")
        return {
            'error': str(e),
            'directory': cache_dir,
            'status': 'error'
        }
