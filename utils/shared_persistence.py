"""
shared_persistence.py - Shared persistence layer for both caching and rate limiting.

This module provides a common abstraction for persisting and retrieving data across
multiple components of the stock pipeline, including the cache system and rate limiter.

Uses diskcache for efficient, thread-safe persistent storage with automatic expiration.
"""

import os
import datetime
from typing import Any, Dict, Optional, List
import logging
from pathlib import Path
import glob
from diskcache import Cache, FanoutCache

# Set up logger for this module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PersistentStore:
    """
    Shared persistence layer for both caching and rate limiting.
    
    Provides a consistent interface for storing and retrieving data with
    automatic expiry, regardless of the specific use case. Uses diskcache
    for efficient, thread-safe persistent storage.
    """
    
    def __init__(self, base_dir: str, create_subdirs: bool = True):
        """
        Initialize persistent store with base directory.
        
        Args:
            base_dir (str): Base directory for storing data
            create_subdirs (bool): Whether to create subdirectories for keys with slashes
        """
        self.base_dir = base_dir
        self.create_subdirs = create_subdirs
        os.makedirs(base_dir, exist_ok=True)
        
        # Use FanoutCache if we need subdirectories (for better concurrency)
        # or regular Cache if flat structure is sufficient
        if create_subdirs:
            self.cache = FanoutCache(base_dir, shards=8)
        else:
            self.cache = Cache(base_dir)
    
    def _process_key(self, key: str) -> str:
        """
        Process key for storage.
        
        Args:
            key (str): Original storage key
            
        Returns:
            str: Processed key ready for use with diskcache
        """
        # diskcache handles hierarchical keys well, so we can use them directly
        # Just ensure any backslashes are converted to forward slashes
        return key.replace('\\', '/')
    
    def save(self, key: str, data: Any, metadata: Optional[Dict] = None, expiry_hours: Optional[float] = None) -> None:
        """
        Save data with optional metadata and expiration.
        
        Args:
            key (str): Storage key
            data (Any): Data to store
            metadata (Dict, optional): Additional metadata to store
            expiry_hours (float, optional): Hours after which the data expires
        """
        try:
            safe_key = self._process_key(key)
            
            # Prepare the data with timestamp and any metadata
            full_data = {
                'data': data,
                'timestamp': datetime.datetime.now().isoformat()
            }
            if metadata:
                full_data.update(metadata)
                
            # Convert expiry_hours to seconds for diskcache
            expire = int(expiry_hours * 3600) if expiry_hours is not None else None
            
            # Store in cache with optional expiration
            self.cache.set(safe_key, full_data, expire=expire)
            logger.debug(f"Saved data for key {key} to diskcache")
            
        except Exception as e:
            logger.error(f"Failed to save data for key {key}: {e}")
    
    def load(self, key: str) -> Optional[Dict]:
        """
        Load data if it exists and hasn't expired.
        
        Args:
            key (str): Storage key
            
        Returns:
            Dict or None: Stored data with metadata, or None if not found
        """
        try:
            safe_key = self._process_key(key)
            return self.cache.get(safe_key)
        except Exception as e:
            logger.error(f"Failed to load data for key {key}: {e}")
            return None
    
    def exists(self, key: str) -> bool:
        """
        Check if data exists for key.
        
        Args:
            key (str): Storage key
            
        Returns:
            bool: True if data exists and hasn't expired, False otherwise
        """
        try:
            safe_key = self._process_key(key)
            return safe_key in self.cache
        except Exception as e:
            logger.error(f"Failed to check if key {key} exists: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete data for key if it exists.
        
        Args:
            key (str): Storage key
            
        Returns:
            bool: True if data was deleted, False if it didn't exist
        """
        try:
            safe_key = self._process_key(key)
            result = self.cache.delete(safe_key)
            if result:
                logger.debug(f"Deleted data for key {key}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete data for key {key}: {e}")
            return False
            
    def list_keys(self, pattern: str = None) -> List[str]:
        """
        List all keys in store, optionally filtered by pattern.
        
        Args:
            pattern (str, optional): Pattern to filter keys (e.g., 'cache/*')
            
        Returns:
            list: List of keys
        """
        try:
            # Create a list from the cache keys
            all_keys = []
            for key in self.cache:
                all_keys.append(key)
            
            # Filter by pattern if provided
            if pattern and all_keys:
                import fnmatch
                all_keys = [k for k in all_keys if fnmatch.fnmatch(str(k), pattern)]
                
            return all_keys
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []
    
    def clear_older_than(self, hours: float) -> int:
        """
        Clear data older than specified hours.
        
        Args:
            hours (float): Number of hours
            
        Returns:
            int: Number of items deleted
        """
        if hours <= 0:
            return 0
        
        count = 0
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        
        # With diskcache, we need to manually check timestamps
        for key in self.list_keys():
            data = self.load(key)
            if not data or 'timestamp' not in data:
                continue
            
            try:
                timestamp = datetime.datetime.fromisoformat(data['timestamp'])
                if timestamp < cutoff:
                    if self.delete(key):
                        count += 1
            except Exception as e:
                logger.error(f"Error processing timestamp for {key}: {e}")
        
        logger.info(f"Cleared {count} items older than {hours} hours from {self.base_dir}")
        return count
    
    def clear_all(self) -> int:
        """
        Clear all data.
        
        Returns:
            int: Number of items deleted
        """
        try:
            # Get count of items first
            count = len(self.cache)
            
            # Clear the cache
            self.cache.clear()
            
            logger.info(f"Cleared all {count} items from {self.base_dir}")
            return count
        except Exception as e:
            logger.error(f"Error clearing all data: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """
        Get stats about the cache.
        
        Returns:
            Dict: Statistics about the cache
        """
        try:
            stats = self.cache.stats()
            return {
                'total_items': len(self.cache),
                'hits': stats[0],
                'misses': stats[1],
                'size': self.cache.volume(),
                'directory': self.base_dir
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'error': str(e),
                'directory': self.base_dir
            }
    
    def close(self) -> None:
        """
        Close the cache and release resources.
        Should be called when done using the store to prevent file locks.
        """
        try:
            if hasattr(self, 'cache') and self.cache is not None:
                self.cache.close()
                logger.debug(f"Closed cache in {self.base_dir}")
        except Exception as e:
            logger.error(f"Error closing cache in {self.base_dir}: {e}")

# Pre-configured instances for common use cases
cache_store = PersistentStore(os.path.join('data', 'cache'), create_subdirs=True)
rate_limit_store = PersistentStore(os.path.join('data', 'rate_limits'), create_subdirs=False)
