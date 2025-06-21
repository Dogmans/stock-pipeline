# Provider API Caching Guide

## Overview

This guide explains how caching works with the data provider APIs in the stock pipeline project. We use diskcache directly to cache API responses and reduce redundant network calls.

## Cache Configuration

All provider caching is handled through the central `cache_config.py` which creates a shared diskcache instance:

```python
from diskcache import FanoutCache

# Global cache instance used throughout the application
cache = FanoutCache('data/cache', shards=8)
```

## Default Expiration Times

Different data types have different cache expiration policies:

| Data Type | Expiration | Reason |
|-----------|------------|--------|
| Historical prices | 24 hours | Prices change daily but rarely need intraday updates |
| Financial statements | 168 hours (1 week) | Rarely change, only quarterly or annually |
| Company overviews | 24 hours | Company data changes infrequently |
| Market data | 6 hours | Market conditions change throughout the day |
| Stock universes | 24 hours | Index compositions change infrequently |

## Example Provider Usage

Each provider implements caching with the same pattern:

```python
from cache_config import cache

class ExampleProvider(BaseDataProvider):
    @cache.memoize(expire=24*3600)  # 24 hours in seconds
    def get_historical_prices(self, symbols, period="1y", interval="1d", force_refresh=False):
        # Force refresh handling
        if force_refresh:
            cache.delete(self.get_historical_prices, symbols, period, interval)
            
        # Actual implementation...
```

## Force Refresh Mechanism

The `force_refresh` parameter bypasses the cache in two ways:

1. When passed to a provider method, it deletes the cache entry before execution:
   ```python
   if force_refresh:
       cache.delete(self.get_method, *args)
   ```

2. It can be propagated through the call stack:
   ```python
   # In stock_data.py
   @cache.memoize(expire=24*3600)
   def get_historical_prices(symbols, period="1y", interval="1d", force_refresh=False, provider=None):
       if force_refresh:
           cache.delete(get_historical_prices, symbols, period, interval, provider)
       
       # Pass force_refresh to the provider
       data_provider = provider or default_provider
       return data_provider.get_historical_prices(symbols, period, interval, force_refresh)
   ```

## Provider-Specific Cache Notes

### Financial Modeling Prep
- Income statements, balance sheets, and cash flows are cached for 1 week
- Historical prices and company overviews are cached for 24 hours
- Rate limiting is handled separately from caching

### YFinance
- All methods have same caching pattern as FMP, with same expiry times
- No explicit API rate limits, but caching prevents excessive calls

### Finnhub
- Has stricter API rate limits, requires both caching and rate limiting
- Same cache expiry pattern as other providers

### Alpha Vantage
- Very restrictive API limits (5 calls per minute, 500 per day)
- Cache expiry is typically longer to avoid hitting limits

## User Experience Features

### Progress Bars
All data providers include progress bars when fetching historical prices for multiple symbols:

```python
# Example from financial_modeling_prep.py
from tqdm import tqdm

def get_historical_prices(self, symbols, period="1y", interval="1d", force_refresh=False):
    # ...
    for symbol in tqdm(symbols, desc="Fetching historical prices", disable=len(symbols) <= 1):
        # fetch data for each symbol
```

Provider-specific implementations:
1. **Financial Modeling Prep**: "Fetching historical prices"
2. **Finnhub**: "Fetching Finnhub prices"  
3. **Alpha Vantage**: "Fetching Alpha Vantage prices"

Progress bars are automatically:
- Displayed when fetching multiple symbols
- Hidden when fetching only a single symbol
- Provide visual feedback on long-running operations

See the daily note from 2025-06-21 for more details on this implementation.
