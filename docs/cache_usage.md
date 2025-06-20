# Cache Usage Guide

This documentation explains how to use the direct diskcache memoization pattern in the stock pipeline project.

## Overview

The stock pipeline now uses the diskcache library directly for caching API results and expensive computations. 
This approach eliminates custom caching logic in favor of the well-tested diskcache implementation.

## How to Use Caching in Your Code

### Basic Caching

To cache the results of a function:

```python
from cache_config import cache

@cache.memoize(expire=24*3600)  # Cache for 24 hours (in seconds)
def my_expensive_function(param1, param2):
    # Expensive computation or API call
    return result
```

### Force Refresh

To support bypassing the cache with a force_refresh parameter:

```python
from cache_config import cache

@cache.memoize(expire=6*3600)  # Cache for 6 hours
def get_market_data(symbol, force_refresh=False):
    # Handle force refresh by deleting cached result
    if force_refresh:
        cache.delete(get_market_data, symbol)
        
    # Function implementation...
    return data
```

### Cache Management

```python
from cache_config import cache, clear_all_cache, get_cache_info

# Clear the entire cache
clear_all_cache()

# Get information about cache
info = get_cache_info()
print(f"Cache contains {info['count']} items using {info['size_kb']} KB")

# Clear just one function's cache
cache.delete(get_market_data)

# Clear specific function call's cache
cache.delete(get_market_data, "AAPL")
```

## Cache Configuration

The cache is configured in `cache_config.py`. The primary settings are:

- **Cache Location**: `data/cache`
- **Cache Type**: `FanoutCache` with 8 shards for better concurrency

If you need to modify cache behavior system-wide, edit the `cache_config.py` file.

## Benefits Over Previous Approach

1. **Simplicity**: No custom serialization/deserialization code
2. **Reliability**: Direct use of the library's tested functionality
3. **Maintainability**: Less code to maintain, fewer potential bugs
4. **Performance**: More efficient key generation and storage
5. **Type Safety**: Better handling of various Python types

## Implementation Notes

- Diskcache automatically handles serialization of most Python types
- Cache keys are generated based on function object and arguments
- Expiry is in seconds, not hours as in the previous implementation
- The cache directory structure is managed automatically by diskcache
