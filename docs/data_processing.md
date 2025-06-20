# Data Processing Workflows

## Caching Pattern

The stock pipeline uses a simple caching mechanism based on the `diskcache` library. This helps reduce API calls and improves performance for data that doesn't change frequently.

### Basic Usage

```python
from cache_config import cache

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def my_expensive_function(param1, param2, force_refresh=False):
    # Handle force_refresh parameter at the beginning
    if force_refresh:
        cache.delete(my_expensive_function, param1, param2)
        
    # Function logic here...
    result = expensive_calculation(param1, param2)
    return result
```

### Key Features

- **Simple Decorator**: Just use the `@cache.memoize(expire=seconds)` decorator
- **Automatic Serialization**: Works with basic Python types, pandas DataFrames, numpy arrays, etc.
- **Force Refresh**: Use the pattern above to allow bypassing the cache when needed
- **Expiration**: Set expiration time in seconds with the `expire` parameter

### Cache Configuration

The cache is configured in `cache_config.py`:

```python
from diskcache import FanoutCache

# Create cache in data/cache directory with 8 shards for better concurrent performance
cache = FanoutCache('data/cache', shards=8)

def clear_all_cache():
    """Clear all cache entries"""
    count = cache.clear()
    return count

def clear_old_cache():
    """Clear only expired cache entries"""
    count = cache.expire()
    return count

def get_cache_info():
    """Get information about cache usage"""
    return {
        'count': len(cache),
        'size': cache.size(),
        'size_mb': cache.size() / (1024 * 1024)
    }
```

### Common Patterns

#### Financial Data Caching

Financial data is typically cached with different expiration times based on how frequently it changes:

- **Price data**: 24 hours (changes daily)
- **Financial statements**: 7 days (changes quarterly)
- **Company information**: 7 days (changes infrequently)

#### Cache Management

To manage the cache during development and production use:

```python
# Clear specific function's cache
from cache_config import cache
from market_data import get_market_conditions
cache.delete(get_market_conditions)

# Clear entire cache
from cache_config import clear_all_cache
clear_all_cache()

# Remove only expired entries
from cache_config import clear_old_cache
clear_old_cache()

# Get cache statistics
from cache_config import get_cache_info
print(get_cache_info())
```
