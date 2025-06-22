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

## Pipeline Commands with Required Universe Parameter

Run screeners directly (now all require universe_df):

```powershell
# Open Python REPL
python

# In Python:
import config
from screeners import screen_for_pe_ratio
from universe import get_stock_universe

# Get a universe DataFrame (required)
universe_df = get_stock_universe("sp500")

# Run screener with required universe_df parameter
results = screen_for_pe_ratio(universe_df)
```

Running the pipeline directly:

```powershell
python -c "import config; from universe import get_stock_universe; from screeners import screen_for_pe_ratio; results = screen_for_pe_ratio(get_stock_universe('sp500')); print(f'Found {len(results)} stocks with low P/E ratios')"
```

## Testing Commands

Run all tests:

```powershell
python -m unittest discover -s tests
```

Run specific test module:

```powershell
python -m unittest tests.test_new_screeners
```

Run tests with coverage:

```powershell
python -m coverage run -m unittest discover -s tests
python -m coverage report
```

Generate HTML coverage report:

```powershell
python -m coverage html
# The report will be available in htmlcov/index.html
```

### New Architecture Testing (Nov 2023)

Test the new screener architecture (direct data access pattern):

```powershell
python -m unittest tests.test_new_screeners
```

Run tests for a specific screener in the new architecture:

```powershell
python -m unittest tests.test_new_screeners.TestNewScreeners.test_pe_ratio_screener
```

Run task for testing all screeners:

```powershell
# Using the VS Code task
code --task "Run All Tests"
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

## Troubleshooting Commands

### Check if TA-Lib is properly installed

```powershell
python -c "import talib; print(f'TA-Lib Version: {talib.__version__}')"
```

### Verify Python environment and versions

```powershell
python -c "import sys, pandas as pd, numpy as np, diskcache; print(f'Python: {sys.version}, Pandas: {pd.__version__}, NumPy: {np.__version__}, diskcache: {diskcache.__version__}')"
```

### Run data processing with debug logs

```powershell
$env:LOG_LEVEL="DEBUG"; python -c "from data_processing import calculate_technical_indicators; import pandas as pd; df = pd.DataFrame({'close': [100, 101, 102], 'high': [102, 103, 104], 'low': [99, 100, 101], 'volume': [1000, 1100, 1200]}); result = calculate_technical_indicators(df); print(result.columns)"
```

### Validate TA-Lib calculations on test data

```powershell
python -c "import talib, numpy as np; close = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]); rsi = talib.RSI(close, timeperiod=14); print(f'RSI result: {rsi}')"
```

### Clear cache and check for errors in specific module

```powershell
python -c "from cache_config import clear_all_cache; clear_all_cache()" && python -c "from data_processing import calculate_technical_indicators; print('Technical indicators module loaded successfully')"
```
