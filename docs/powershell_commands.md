# PowerShell Commands for Cache Management

## Cache Management

Clear all cache entries:

```powershell
python -c "from cache_config import clear_all_cache; print(f'Cleared {clear_all_cache()} cache entries')"
```

Get cache information:

```powershell
python -c "from cache_config import get_cache_info; print(get_cache_info())"
```

## Pipeline Execution

Run full pipeline with cache clearing:

```powershell
python main.py --clear-cache --full
```

Run pipeline for specific universe with latest data:

```powershell
python main.py --universe sp500 --clear-cache
```

## Testing With Cache Control

Test a specific module with fresh data:

```powershell
# First clear any cached data that might affect the test
python -c "from cache_config import cache; cache.clear()"

# Then run the specific test 
python -m unittest tests.test_market_data
```

Run all tests with clean cache:

```powershell
python -c "from cache_config import cache; cache.clear()" && python -m unittest discover -s tests
```

## Cache Diagnostics

Count cache entries:

```powershell
python -c "from cache_config import cache; print(f'Cache has {len(cache)} entries')"
```

Check cache size in KB:

```powershell
python -c "from cache_config import cache; print(f'Cache size: {cache.volume() / 1024:.2f} KB')"
```

Cache hit/miss statistics:

```powershell
python -c "from cache_config import cache; hits, misses = cache.stats(); print(f'Hits: {hits}, Misses: {misses}, Hit ratio: {hits/(hits+misses or 1):.1%}')"
```

## Working Examples

Get market conditions with fresh data:

```powershell
python -c "from market_data import get_market_conditions; from cache_config import cache; cache.delete(get_market_conditions); result = get_market_conditions(); print(f'Retrieved {len(result)} market indexes')"
```

Get stock universe after clearing cache:

```powershell
python -c "from universe import get_stock_universe; from cache_config import cache; cache.delete(get_stock_universe); df = get_stock_universe('sp500'); print(f'Retrieved {len(df)} symbols')"
```
