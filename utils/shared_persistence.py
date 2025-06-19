"""
shared_persistence.py - Shared persistence layer for both caching and rate limiting.

This module provides a common abstraction for persisting and retrieving data across
multiple components of the stock pipeline, including the cache system and rate limiter.

Uses Python's built-in shelve module for dictionary-like persistent storage.
"""

import os
import shelve
import datetime
from typing import Any, Dict, Optional, List
import logging
from pathlib import Path
import glob
import pickle  # For serializing complex Python objects

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
    timestamp tracking, regardless of the specific use case. Uses Python's
    built-in shelve module for dictionary-like persistent storage.
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
        self.main_db_path = os.path.join(base_dir, 'store')
        os.makedirs(base_dir, exist_ok=True)
        
    def _get_db_path(self, subdir: str = None) -> str:
        """
        Get the database path for a specific subdirectory.
        
        Args:
            subdir (str, optional): Subdirectory name
            
        Returns:
            str: Path to the shelve database
        """
        if subdir:
            path = os.path.join(self.base_dir, subdir, 'store')
            os.makedirs(os.path.join(self.base_dir, subdir), exist_ok=True)
            return path
        return self.main_db_path
    
    def _get_db_and_key(self, key: str) -> tuple:
        """
        Get the appropriate database path and processed key for a storage key.
        
        Args:
            key (str): Storage key, can include slashes for subdirectories
            
        Returns:
            tuple: (db_path, safe_key)
        """
        if self.create_subdirs and '/' in key:
            # Handle keys with subdirectory structure
            parts = key.split('/')
            safe_key = parts.pop()  # Last part is the key
            subdir = os.path.join(*parts)  # Rest are subdirectory
            db_path = self._get_db_path(subdir)
            return db_path, safe_key
        else:
            # Simple flat storage
            safe_key = key.replace('/', '_').replace('\\', '_')
            return self.main_db_path, safe_key
    
    def save(self, key: str, data: Any, metadata: Optional[Dict] = None) -> None:
        """
        Save data with optional metadata.
        
        Args:
            key (str): Storage key
            data (Any): Data to store
            metadata (Dict, optional): Additional metadata to store
        """
        try:
            db_path, safe_key = self._get_db_and_key(key)
            
            full_data = {
                'data': data,
                'timestamp': datetime.datetime.now().isoformat(),
            }
            if metadata:
                full_data.update(metadata)
                
            with shelve.open(db_path, writeback=True) as db:
                db[safe_key] = full_data
                
            logger.debug(f"Saved data for key {key} to shelve database")
        except Exception as e:
            logger.error(f"Failed to save data for key {key}: {e}")
            
    def load(self, key: str) -> Optional[Dict]:
        """
        Load data if it exists.
        
        Args:
            key (str): Storage key
            
        Returns:
            Dict or None: Stored data with metadata, or None if not found
        """
        try:
            db_path, safe_key = self._get_db_and_key(key)
            
            with shelve.open(db_path) as db:
                if safe_key in db:
                    return db[safe_key]
                return None
        except Exception as e:
            logger.error(f"Failed to load data for key {key}: {e}")
            return None
            
    def exists(self, key: str) -> bool:
        """
        Check if data exists for key.
        
        Args:
            key (str): Storage key
            
        Returns:
            bool: True if data exists, False otherwise
        """
        try:
            db_path, safe_key = self._get_db_and_key(key)
            with shelve.open(db_path) as db:
                return safe_key in db
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
            db_path, safe_key = self._get_db_and_key(key)
            with shelve.open(db_path, writeback=True) as db:
                if safe_key in db:
                    del db[safe_key]
                    logger.debug(f"Deleted data for key {key}")
                    return True
                return False
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
        all_keys = []
        
        try:
            if self.create_subdirs:
                # For nested structure, we need to scan directories and open shelve DBs
                for dirpath, dirnames, filenames in os.walk(self.base_dir):
                    # Find shelve database files (they have .db or .dat extensions)
                    shelve_files = [f for f in filenames if f.startswith('store.') and
                                    (f.endswith('.db') or f.endswith('.dat'))]
                    
                    if shelve_files:
                        # This directory has a shelve database
                        rel_path = os.path.relpath(dirpath, self.base_dir)
                        db_path = os.path.join(dirpath, 'store')
                        
                        with shelve.open(db_path) as db:
                            # Create full keys with path prefix unless it's the root
                            prefix = '' if rel_path == '.' else f"{rel_path}/"
                            keys = [f"{prefix}{key}" for key in db.keys()]
                            all_keys.extend(keys)
            else:
                # Simple flat storage - just one shelve database
                if os.path.exists(f"{self.main_db_path}.db") or \
                   os.path.exists(f"{self.main_db_path}.dat"):
                    with shelve.open(self.main_db_path) as db:
                        all_keys = list(db.keys())
            
            # Filter by pattern if provided
            if pattern and all_keys:
                import fnmatch
                all_keys = [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
                
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
        count = 0
        for key in self.list_keys():
            if self.delete(key):
                count += 1
                
        logger.info(f"Cleared all {count} items from {self.base_dir}")
        return count
      # Migration code removed as it's not needed

# Pre-configured instances for common use cases
cache_store = PersistentStore(os.path.join('data', 'cache'), create_subdirs=True)
rate_limit_store = PersistentStore(os.path.join('data', 'rate_limits'), create_subdirs=False)
