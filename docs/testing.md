# Testing with Cache System

## Overview

This document explains how to work with the caching system during testing.

## Screener Testing

### Testing Analyst Sentiment Momentum Screener

**Individual Stock Testing**:
```python
# Test analyst sentiment screener with specific stocks
from screeners.analyst_sentiment_momentum import screen_for_analyst_sentiment_momentum
import pandas as pd

# Create test universe with known analyst coverage
test_universe = pd.DataFrame({
    'symbol': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA'],
    'security': ['Apple Inc', 'Microsoft Corp', 'NVIDIA Corp', 'Alphabet Inc', 'Tesla Inc'],
    'gics_sector': ['Technology'] * 5,
    'gics_sub_industry': ['Technology Hardware', 'Software', 'Semiconductors', 'Internet', 'Auto Manufacturers']
})

# Run screener
results = screen_for_analyst_sentiment_momentum(test_universe)
print(f"Found {len(results)} stocks with positive analyst sentiment")
print(results[['symbol', 'analyst_momentum_score', 'reason']].head())
```

**Expected Performance Metrics**:
- **Processing Speed**: ~2-3 seconds per stock (due to multiple API calls)
- **API Calls**: 5 endpoints per stock (grades, consensus, estimates, targets, historical)
- **Data Volume**: 50+ analyst ratings processed per covered stock
- **Scoring Range**: 0-100 points with weighted multi-component system
- **Coverage**: 85%+ of large-cap stocks have sufficient analyst coverage
- **Success Rate**: 10-30% of S&P 500 stocks typically pass screening criteria

**Component Testing**:
```python
# Test individual scoring components
from screeners.analyst_sentiment_momentum import AnalystSentimentMomentumScreener

screener = AnalystSentimentMomentumScreener()

# Test grade change analysis
test_symbol = 'AAPL'
grade_score = screener._calculate_rating_momentum_score(grade_data, test_symbol)
print(f"Rating momentum score for {test_symbol}: {grade_score}")

# Validate scoring thresholds
assert 0 <= grade_score <= 30, "Rating score should be between 0-30 points"
```

**API Endpoint Validation**:
```python
# Direct endpoint testing for troubleshooting
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider

provider = FinancialModelingPrepProvider()

# Test primary grade endpoint
grade_data = provider.get_analyst_grades('AAPL')
print(f"Grade data records: {len(grade_data) if grade_data else 0}")

# Test auxiliary endpoints
targets = provider.get_analyst_price_targets('AAPL')
estimates = provider.get_analyst_estimates('AAPL')
print(f"Price targets: {len(targets) if targets else 'None'}")
print(f"Estimates: {len(estimates) if estimates else 'None'}")
```

**Error Handling Validation**:
```python
# Test graceful degradation with limited data
test_cases = [
    'AAPL',  # High coverage stock
    'TSLA',  # Volatile analyst coverage
    'XYZ123'  # Invalid symbol (should handle gracefully)
]

for symbol in test_cases:
    try:
        result = screen_for_analyst_sentiment_momentum(
            pd.DataFrame({'symbol': [symbol], 'security': [f'{symbol} Test']})
        )
        print(f"{symbol}: {'Pass' if len(result) > 0 else 'Filtered out'}")
    except Exception as e:
        print(f"{symbol}: Error handled - {str(e)[:50]}...")
```

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

## Test Files Organization (Updated June 2025)

The test files are organized to align with our current architecture:

### Core Test Files

1. `test_screeners.py` - Tests the new screener architecture where each screener fetches its own data
2. `test_providers.py` - Tests data providers with their API-specific methods
3. `test_providers.py` - Tests data provider functionality
4. `test_cache.py` - Tests the caching system

### Other Test Files

- `test_config.py` - Tests configuration loading
- `test_market_data.py` - Tests market data retrieval
- `test_providers.py` - Tests data provider functionality 
- `test_universe.py` - Tests universe selection functions
- `test_visualization.py` - Tests visualization functions
- `test_utils.py` - Tests utility functions
- `test_main.py` - Tests the main pipeline orchestration

### Removed Test Files (June 2025)

As part of our refactoring, we removed the following redundant test files:

1. `test_run_pipeline.py` - Empty file that was no longer needed
2. `test_simple.py` - Contained only trivial placeholder tests

## Running Tests with VS Code Tasks

We have several VS Code tasks to simplify test execution:

```json
{
  "label": "Run All Tests",
  "type": "shell",
  "command": "python",
  "args": ["-m", "unittest", "discover", "-s", "tests"],
  "group": "test"
},
{
  "label": "Run All Tests with Coverage",
  "type": "shell",
  "command": "python",
  "args": ["-m", "coverage", "run", "-m", "unittest", "discover", "-s", "tests", "&&", "python", "-m", "coverage", "report"],
  "group": "test"
}
```

## Special Considerations

1. **Tests That Modify Cache**: If your test modifies the cache behavior, be sure to restore the original state in the `tearDown` method.

2. **Integration Tests**: Integration tests might benefit from using the cache to avoid hitting external APIs repeatedly.

3. **Performance Tests**: For performance testing, it's important to run both with cold cache and warm cache to understand both scenarios.
