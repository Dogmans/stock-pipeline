# PowerShell Commands for Cache Management

## VS Code Debug Configurations

The project includes pre-configured VS Code debug configurations for common scenarios:

### Available Debug Configurations:
- **Debug SP500 All Strategies**: Run all screeners on S&P 500 (limit: 50)
- **Debug Russell2000 All Strategies**: Run all screeners on Russell 2000 (limit: 50)
- **Debug SP500 High Performance**: Run high-performance screeners on S&P 500 (limit: 30)
- **Debug Russell2000 Traditional Value**: Run traditional value screeners on Russell 2000 (limit: 30)
- **Debug Custom Stock List**: Test specific stocks with selected screeners
- **Debug with Cache Info**: Run with cache information display
- **Debug Force Refresh**: Run with fresh data (bypass cache)

### Available Tasks:
- **Run SP500 All Strategies**: Execute without debugging
- **Run Russell2000 All Strategies**: Execute without debugging  
- **Run SP500 High Performance**: Execute high-performance screeners
- **Run Russell2000 Traditional Value**: Execute traditional value screeners
- **Test Individual Screeners**: Test on sample stocks
- **Clear Cache**: Clear all cached data
- **Show Cache Info**: Display cache statistics

### Usage:
1. Press `F5` to start debugging with the default configuration
2. Press `Ctrl+Shift+P` and type "Debug: Select and Start Debugging" to choose a specific configuration
3. Press `Ctrl+Shift+P` and type "Tasks: Run Task" to execute tasks without debugging

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

## Historic Value Screener Examples

Test the new historic value screener:

```powershell
# Run historic value screening on S&P 500
python main.py --universe sp500 --strategies historic_value --limit 15

# Combine historic value with quality metrics
python main.py --universe sp500 --strategies historic_value,quality,fcf_yield --limit 10

# Force refresh for latest data
python main.py --universe sp500 --strategies historic_value --force-refresh --limit 20

# Test on Russell 2000 for smaller cap opportunities  
python main.py --universe russell2000 --strategies historic_value --limit 25
```

Expected output: 400-450 stocks from S&P 500 meet basic criteria, with top candidates showing scores around 25-30/100.

Run pipeline for specific universe with latest data:

```powershell
python main.py --universe sp500 --clear-cache
```

Run pipeline with specific screeners:

```powershell
# Run the pipeline with PE ratio screener
python main.py --universe sp500 --strategies pe_ratio

# Run with multiple screeners
python main.py --universe sp500 --strategies pe_ratio,price_to_book,peg_ratio

# Run all available screeners
python main.py --strategies all

# Customize the display limit (default is 20 for non-combined screeners)
python main.py --strategies pe_ratio --limit 30
python main.py --strategies pe_ratio --limit 10

# For combined screeners, the default limit is 10
python main.py --strategies combined --limit 5
```

## Display Limits

As of July 3, 2025, the pipeline has the following default display limits:

- Non-combined screeners: 20 stocks (previously unlimited)
- Combined screener: 10 stocks

This helps manage the large number of results from Russell 2000 screeners. You can override these defaults with the `--limit` parameter.

To show all results (no limit), use `--limit 0`:

```powershell
# Display all matching stocks (potentially hundreds for Russell 2000)
python main.py --universe russell2000 --strategies pe_ratio --limit 0
```

## VS Code Tasks

The following tasks can be run using the VS Code Command Palette (Ctrl+Shift+P) with "Tasks: Run Task":

### Pipeline Tasks

| Task Name | Description | Command |
|-----------|-------------|---------|
| Run Full Pipeline | Runs all strategies on all universes | `python main.py --universe all --strategies all` |
| Run Full Pipeline with Cache Clear | Runs all strategies on all universes with fresh data | `python main.py --universe all --strategies all --clear-cache` |
| Run Quick Pipeline | Runs value and growth strategies on SP500 | `python main.py --universe sp500 --strategies value,growth` |
| Run Value Pipeline | Runs value strategy on SP500 | `python main.py --universe sp500 --strategies value` |
| Clear Cache & Run Pipeline | Clears cache and runs full pipeline | `python main.py --clear-cache --full` |
| Run Russell 2000 Pipeline | Runs all strategies on Russell 2000 stocks | `python main.py --universe russell2000 --strategies all` |

### Testing Tasks

| Task Name | Description | Command |
|-----------|-------------|---------|
| Run All Tests | Runs all unit tests | `python -m unittest discover -s tests` |
| Run All Tests with Coverage | Runs all unit tests and generates coverage report | `python -m coverage run -m unittest discover -s tests && python -m coverage report` |
| Run Test Module | Prompts for test module path and runs it | `python -m unittest ${input:testModulePath}` |
| Run Pipeline with Sequential Tests | Runs the pipeline with sequential tests | `./run_sequential_tests.ps1` |
| Generate HTML Coverage Report | Creates HTML coverage report | `python -m coverage html` |

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
$env:LOG_LEVEL="DEBUG"; python -c "from technical_indicators import calculate_technical_indicators; import pandas as pd; df = pd.DataFrame({'close': [100, 101, 102], 'high': [102, 103, 104], 'low': [99, 100, 101], 'volume': [1000, 1100, 1200]}); result = calculate_technical_indicators(df); print(result.columns)"
```

### Validate TA-Lib calculations on test data

```powershell
python -c "import talib, numpy as np; close = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]); rsi = talib.RSI(close, timeperiod=14); print(f'RSI result: {rsi}')"
```

### Clear cache and check for errors in specific module

```powershell
python -c "from cache_config import clear_all_cache; clear_all_cache()" && python -c "from technical_indicators import calculate_technical_indicators; print('Technical indicators module loaded successfully')"
```

# Testing Specific Screeners

## Testing the Fallen IPO Screener

Run just the fallen IPO screener with a small universe to test exception handling:

```powershell
python -c "import pandas as pd; from screeners import screen_for_fallen_ipos; df = pd.DataFrame({'symbol': ['AAPL', 'MSFT', 'NVDA']}); results = screen_for_fallen_ipos(df); print(f'Found {len(results)} results')"
```

Using a specific list of recent IPOs for more targeted testing:

```powershell
python -c "import pandas as pd; from screeners import screen_for_fallen_ipos; df = pd.DataFrame({'symbol': ['RIVN', 'UBER', 'LYFT', 'DASH', 'ABNB']}); results = screen_for_fallen_ipos(df, max_years_since_ipo=5); print(results)"
```

## Special Screeners

Run turnaround companies screener:

```powershell
python -c "
import pandas as pd
from universe import get_stock_universe
from screeners import screen_for_turnaround_candidates

# Get stock universe
universe = get_stock_universe('sp500')

# Run the turnaround screener
results = screen_for_turnaround_candidates(universe)

# Display top results
if not results.empty:
    print(f'Found {len(results)} potential turnaround candidates')
    print('\nTop 10 turnaround candidates:')
    columns = ['symbol', 'company_name', 'sector', 'turnaround_score', 
               'eps_trend', 'revenue_trend', 'latest_eps', 'eps_change']
    print(results[columns].head(10).to_string(index=False))
else:
    print('No turnaround candidates found')
"
```

Generate detailed turnaround analysis report:

```powershell
python -c "
import pandas as pd
from universe import get_stock_universe
from screeners import screen_for_turnaround_candidates
import matplotlib.pyplot as plt
import os

# Create output directory if it doesn't exist
os.makedirs('output/turnaround_analysis', exist_ok=True)

# Get stock universe
universe = get_stock_universe('sp500')

# Run the turnaround screener
results = screen_for_turnaround_candidates(universe)

if not results.empty:
    # Save results to CSV
    results.to_csv('output/turnaround_analysis/turnaround_candidates.csv', index=False)
    
    # Create a simple visualization of scores
    plt.figure(figsize=(10, 8))
    top_10 = results.head(10)
    plt.barh(top_10['symbol'], top_10['turnaround_score'], color='green')
    plt.xlabel('Turnaround Score')
    plt.ylabel('Company Symbol')
    plt.title('Top 10 Companies Showing Signs of Turning the Corner')
    plt.tight_layout()
    plt.savefig('output/turnaround_analysis/top_turnaround_scores.png')
    
    print(f'Saved detailed results to output/turnaround_analysis/')
"
```

## Using the Turnaround Screener Scripts

Run the complete turnaround screener test suite:

```powershell
.\scripts\powershell\test_turnaround_screener.ps1
```

This script:
1. Tests the turnaround screener on S&P 500 and Russell 2000 universes
2. Saves results to CSV files in the output/turnaround_analysis directory
3. Captures all output to a timestamped log file
4. Displays summary statistics by sector, score, and primary factor

Run the turnaround screener unit tests:

```powershell
python -m unittest tests/test_turnaround_screener_logic.py
```

Force refresh financial data when running the screener:

```powershell
python -c "
from screeners import screen_for_turnaround_candidates
import universe

# Get stock universe
sp500 = universe.get_sp500_universe()

# Run screener with force_refresh=True to bypass cache
results = screen_for_turnaround_candidates(sp500, force_refresh=True)
print(f'Found {len(results)} potential turnaround candidates')
if not results.empty:
    print(results[['symbol', 'name', 'primary_factor', 'turnaround_score']])
"
```

## Screener Enhanced Behavior (2025-06-30)

Run a screener and examine all results vs. threshold-filtered results:

```powershell
# Get all stocks with valid P/E ratios and show both full set and filtered
python -c "from screeners import screen_for_pe_ratio; from universe import get_stock_universe; results = screen_for_pe_ratio(get_stock_universe()); print(f'Total stocks with valid P/E: {len(results)}'); print(f'Stocks meeting threshold: {len(results[results.meets_threshold == True])}')"
```

Run the combined screener with different input strategies (shows only stocks that appear in ALL specified screeners):

```powershell
# Run combined screener with custom strategy set
python -c "from screeners import screen_for_combined; from universe import get_stock_universe; results = screen_for_combined(get_stock_universe(), strategies=['pe_ratio', 'peg_ratio']); print(results[['symbol', 'avg_rank', 'screener_count', 'metrics_summary']].head(10))"
```

Debug the metrics that went into combined score calculation:

```powershell
# See detailed ranks from each screener
python -c "from screeners import screen_for_combined; from universe import get_stock_universe; results = screen_for_combined(get_stock_universe()); print(results[['symbol', 'rank_details']].head(5))"
```

## Project Cleanup

Remove temporary debug and test files:

```powershell
# Remove all debug files created during troubleshooting
Remove-Item "debug_*.py" -ErrorAction SilentlyContinue

# Remove temporary test files
Remove-Item "test_*fix*.py" -ErrorAction SilentlyContinue

# Remove multiple files at once
Remove-Item "debug_universe.py", "debug_universe2.py", "debug_fcf.py", "debug_price_to_book.py", "test_price_to_book_fix.py" -ErrorAction SilentlyContinue
```

Verify cleanup:

```powershell
# Check for any remaining temporary files
Get-ChildItem -Name "debug_*.py", "test_*fix*.py" -ErrorAction SilentlyContinue

# List all temporary files in project
Get-ChildItem -Name "*.tmp", "*debug*", "*temp*" -Recurse -ErrorAction SilentlyContinue
```

## Performance Optimization - Cache-Aware Throttling

### Test Cache-Aware Throttling Performance
```powershell
# Test throttling performance with cache awareness
python test_cache_aware_throttling.py

# Expected output shows dramatic speed improvement for cached requests:
# First API call:  1.20s
# Cached call:     0.01s (0.8% of original)
# Cache speed improvement: 120.0x faster
```

### Compare Pipeline Performance Before/After
```powershell
# Run same screener multiple times to see caching benefit
python main.py --universe sp500 --strategies enhanced_quality --limit 10

# First run: ~5-10 minutes (fresh API calls)
# Second run: ~30-60 seconds (mostly cached data)
```

### Monitor Rate Limiting Behavior
```powershell
# Enable debug logging to see throttling decisions
$env:LOG_LEVEL="DEBUG"
python main.py --universe sp500 --strategies pe_ratio --limit 5

# Should show:
# - "Rate limit: sleeping Xs" for fresh API calls
# - No throttling messages for cached requests
```

### Performance Testing Commands
```powershell
# Test single screener performance
Measure-Command { python main.py --universe sp500 --strategies enhanced_quality --limit 50 }

# Test multiple screener performance  
Measure-Command { python main.py --universe sp500 --strategies enhanced_quality,momentum --limit 20 }

# Clear cache to test fresh API call performance
Remove-Item -Path "data\cache" -Recurse -Force -ErrorAction SilentlyContinue
Measure-Command { python main.py --universe sp500 --strategies enhanced_quality --limit 10 }
```

### Expected Performance Improvements

| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| Cached requests | 0.5-2.0s | 0.01s | 50-200x faster |
| Fresh API calls | 0.5-2.0s | 0.5-2.0s | No change (appropriate) |
| Repeated pipeline runs | Same as first | 95% faster | Massive improvement |
| Large universe analysis | Linear degradation | Cached acceleration | Exponential improvement |

### Troubleshooting Performance Issues

```powershell
# Check if throttling is the bottleneck
$env:LOG_LEVEL="DEBUG"
python -c "
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
import time
provider = FinancialModelingPrepProvider()
start = time.time()
data = provider.get_company_overview('AAPL')
print(f'Time: {time.time()-start:.2f}s, Retrieved: {bool(data)}')
"

# Clear cache if corrupted
Remove-Item -Path "data\cache" -Recurse -Force -ErrorAction SilentlyContinue

# Test network connectivity
Test-NetConnection financialmodelingprep.com -Port 443
```
