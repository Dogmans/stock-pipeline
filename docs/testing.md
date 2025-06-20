# Testing with Cache System

## Overview

This document explains how to work with the caching system during testing.

## Cache Handling in Tests

The stock pipeline's test suite interacts with the cache system in various ways:

1. **Default Behavior**: Tests use the cache just like the regular application
2. **Clearing Cache**: Some tests need a clean cache to ensure predictable results
3. **Force Refresh**: Tests can bypass the cache when needed
4. **Mock Caching**: For unit tests, the cache can be mocked

## Strategies for Testing with Cache

### Clearing Cache Before Tests

```python
import unittest
from cache_config import cache

class TestMarketData(unittest.TestCase):
    def setUp(self):
        # Clear relevant cache entries before each test
        cache.delete('get_market_conditions')
        
    def test_market_conditions(self):
        # This will execute with a clean cache
        result = get_market_conditions()
        self.assertIsNotNone(result)
```

### Using Force Refresh

```python
def test_historical_prices_with_fresh_data(self):
    # Use force_refresh to bypass cache
    prices = get_historical_prices(['AAPL', 'MSFT'], force_refresh=True)
    self.assertIsNotNone(prices)
```

### Testing Cache Hits

```python
def test_cache_hit(self):
    # First call will miss cache
    first_call = get_market_conditions()
    
    # Get cache stats
    hits_before, misses_before = cache.stats()
    
    # Second call should hit cache
    second_call = get_market_conditions()
    
    # Get updated stats
    hits_after, misses_after = cache.stats()
    
    # Verify cache was hit
    self.assertEqual(hits_after, hits_before + 1)
    self.assertEqual(misses_after, misses_before)
```

## Mocking the Cache for Unit Tests

For true unit tests, you may want to mock the cache:

```python
from unittest.mock import patch

@patch('cache_config.cache.memoize', lambda *args, **kwargs: lambda f: f)
def test_function_without_caching(self):
    # This will bypass the cache decorator entirely
    result = my_cached_function()
    self.assertIsNotNone(result)
```

## Testing Cache Expiration

Cache expiration can be tested by manipulating the expire parameter:

```python
def test_cache_expiration(self):
    from cache_config import cache
    
    # Create a function with 1 second expiry for testing
    @cache.memoize(expire=1)
    def quick_expire_func():
        return datetime.now().timestamp()
    
    # First call
    first_val = quick_expire_func()
    
    # Immediate second call should return same value (cache hit)
    self.assertEqual(quick_expire_func(), first_val)
    
    # Wait for expiration
    time.sleep(1.1)
    
    # After expiry, should get new value
    self.assertNotEqual(quick_expire_func(), first_val)
```

## Running Test Suite with Clean Cache

To run the entire test suite with a clean cache, use this command:

```bash
python -c "from cache_config import cache; cache.clear()" && python -m unittest discover -s tests
```

## Special Considerations

1. **Tests That Modify Cache**: If your test modifies the cache behavior, be sure to restore the original state in the `tearDown` method.

2. **Integration Tests**: Integration tests might benefit from using the cache to avoid hitting external APIs repeatedly.

3. **Performance Tests**: For performance testing, it's important to run both with cold cache and warm cache to understand both scenarios.
