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

## TA-Lib Technical Indicators

When using the TA-Lib library for technical indicators, always convert pandas Series to NumPy arrays using `.values`:

```python
# CORRECT - Convert pandas Series to NumPy array
df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)

# INCORRECT - This will cause "input array type is not double" error
df['rsi'] = talib.RSI(df['close'], timeperiod=14)
```

### Common TA-Lib Patterns

Follow these patterns for various indicator types:

#### Single-Array Indicators

```python
# RSI calculation
df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)

# Moving averages
df['sma_20'] = talib.SMA(df['close'].values, timeperiod=20)
df['ema_12'] = talib.EMA(df['close'].values, timeperiod=12)
```

#### Multi-Array Indicators

```python
# Bollinger Bands (returns 3 arrays)
df['upper_band'], df['middle_band'], df['lower_band'] = talib.BBANDS(
    df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
)

# Stochastic (returns 2 arrays)
df['slowk'], df['slowd'] = talib.STOCH(
    df['high'].values, df['low'].values, df['close'].values,
    fastk_period=14, slowk_period=3, slowd_period=3
)
```

#### Volume-Based Indicators

```python
# On Balance Volume
df['obv'] = talib.OBV(df['close'].values, df['volume'].values)
```

### Special Case: On Balance Volume (OBV)

For some indicators like OBV, you may need to explicitly convert to float:

```python
# Additional type conversion may be needed for OBV
close_values = df['close'].values.astype(float)
volume_values = df['volume'].values.astype(float)
df['obv'] = talib.OBV(close_values, volume_values)
```

This is because OBV is particularly sensitive to data types and may fail with "input array type is not double" even when using .values, if there are any non-numeric values or if the array's underlying type isn't explicitly float.

### Error Handling

Always wrap TA-Lib calls in try-except blocks to handle potential errors:

```python
try:
    df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
except Exception as e:
    logger.error(f"Error calculating RSI: {e}")
    # Fallback to pandas implementation or leave column empty
```

### Troubleshooting TA-Lib Errors

#### Common Error: "input array type is not double"

This error occurs when passing pandas Series directly to TA-Lib functions instead of converting them to NumPy arrays with `.values`.

```python
# This will cause an error
df['rsi'] = talib.RSI(df['close'], timeperiod=14)

# This will work correctly
df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
```

#### Providing Fallbacks

Always provide pandas fallback implementations when TA-Lib is not available:

```python
# Check if TA-Lib is available
if HAS_TALIB:
    try:
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
    except Exception as e:
        logger.error(f"Error calculating TA-Lib indicators: {e}")
else:
    # Fallback to pandas implementation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
```

#### Avoiding Duplicate Calculations

Be careful not to calculate the same indicators multiple times in different parts of the code. This can lead to:

1. Performance issues
2. Different values for the same indicators if implementations differ
3. Confusion when debugging

The solution is to centralize all indicator calculations in one place, like the `calculate_technical_indicators` function.

#### Best Practice: Unified Technical Indicator Calculation

```python
def calculate_technical_indicators(df):
    """Calculate all technical indicators in one place"""
    
    # Try TA-Lib first for better accuracy
    if HAS_TALIB:
        try:
            # Always use .values with TA-Lib
            df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
            # More TA-Lib indicators...
        except Exception as e:
            logger.error(f"TA-Lib error: {e}")
            # Fall back to pandas implementations
            calculate_pandas_indicators(df)
    else:
        # No TA-Lib, use pandas implementations
        calculate_pandas_indicators(df)
    
    return df
```

## Text Encoding and Unicode Handling

### Unicode Issues in Output Files

When generating output files (especially on Windows systems), be aware that certain Unicode characters may cause encoding errors. This is particularly true for console output and text files written without explicitly specifying an encoding.

#### Common Issues

- Unicode arrows (→, ↑, ↓) may cause UnicodeEncodeError on Windows
- Special characters in company names or descriptions from external APIs
- Currency symbols (€, £, ¥) in financial data

#### Best Practices

1. **Use ASCII Alternatives When Possible**:
   ```python
   # Instead of:
   text = "Price movement: ↑ 5.2%"
   
   # Use:
   text = "Price movement: UP 5.2%"  # or
   text = "Price movement: ^^ 5.2%"  # or 
   text = "Price movement: (+5.2%)"
   ```

2. **Replace Unicode Characters in Output**:
   ```python
   # Example from main.py turnaround candidates
   primary_factor = row['primary_factor'].replace('→', '->')
   ```

3. **Specify Encoding When Opening Files**:
   ```python
   with open('output.txt', 'w', encoding='utf-8') as f:
       f.write("Contains Unicode: →")
   ```

4. **Handle Potential Encoding Issues in Data Processing**:
   ```python
   def sanitize_for_output(text):
       """Replace Unicode characters with ASCII equivalents for output compatibility."""
       replacements = {
           '→': '->',
           '↑': 'UP',
           '↓': 'DOWN',
           '✓': 'PASS',
           '✗': 'FAIL',
       }
       
       for unicode_char, ascii_replacement in replacements.items():
           text = text.replace(unicode_char, ascii_replacement)
       
       return text
   ```

Using these practices ensures maximum compatibility across different operating systems and console environments.

## Universe-Based Output Filenames

Output files are now named based on the universe parameter used when running the pipeline:

### File Naming Convention

When running the pipeline with a specific universe (e.g., `--universe sp500`), the output files will include the universe name in their filename:

```
# Original naming pattern
output/screening_report.md
output/summary.txt

# New naming pattern
output/screening_report_<universe>.md
output/summary_<universe>.txt
```

### Examples

Running with `--universe sp500`:
```
output/screening_report_sp500.md
output/summary_sp500.txt
```

Running with `--universe russell2000`:
```
output/screening_report_russell2000.md
output/summary_russell2000.txt
```

This makes it easier to maintain and compare results from multiple universes without overwriting files.

### Implementation

The filename transformation happens automatically when running the pipeline, using the `get_universe_filename()` function in `main.py`. No changes to command-line usage are required.

```python
def get_universe_filename(base_filename, universe):
    """Create a filename that incorporates the universe name."""
    name_parts = base_filename.rsplit('.', 1)
    if len(name_parts) == 2:
        base_name, extension = name_parts
        return f"{base_name}_{universe}.{extension}"
    else:
        return f"{base_filename}_{universe}"
```
