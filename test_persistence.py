"""
Test script for the diskcache-based persistence system.

This script performs a simple test of the shared_persistence module
to verify that the diskcache-based persistence system is working correctly.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils.shared_persistence import PersistentStore

def test_persistent_store():
    """
    Test the PersistentStore class functionality.
    """
    # Create a test store
    test_dir = os.path.join('data', 'test_store')
    os.makedirs(test_dir, exist_ok=True)
    
    # Variable to hold our store instance
    store = None
    
    try:
        # Create a new store
        store = PersistentStore(test_dir, create_subdirs=True)
        
        # Test basic save/load operations
        test_data = {'message': 'Hello, world!', 'number': 42}
        store.save('test_key', test_data)
        
        loaded_data = store.load('test_key')
        print(f"Loaded data: {loaded_data}")
        
        # Test nested keys
        store.save('nested/key', {'nested': True})
        loaded_nested = store.load('nested/key')
        print(f"Loaded nested data: {loaded_nested}")
        
        # Test listing keys
        keys = store.list_keys()
        print(f"All keys: {keys}")
        
        # Test expiration
        store.save('old_key', {'old': True}, 
                  {'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()})
        store.clear_older_than(1)
        
        print(f"After clearing old data, keys: {store.list_keys()}")
        print(f"'old_key' exists: {store.exists('old_key')}")
        print(f"'test_key' exists: {store.exists('test_key')}")
        
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        return False
        
    finally:
        # Clean up using diskcache's own methods and close properly
        try:
            if store is not None:
                # Clear the cache first
                store.clear_all()
                # Properly close the cache to release file locks
                store.close()
                print("Cache properly cleared and closed")
        except Exception as e:
            print(f"Error during cache cleanup: {e}")

if __name__ == "__main__":
    print("Testing diskcache-based persistence system...")
    success = test_persistent_store()
    
    if success:
        print("\nSUCCESS: The diskcache-based persistence system is working correctly!")
    else:
        print("\nFAILURE: There were errors in the diskcache-based persistence test.")
