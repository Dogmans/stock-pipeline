# Data Processing Workflows

## Analyst Sentiment Processing

**Analyst Sentiment Momentum Screener Pipeline**:

1. **Data Collection Phase**:
   - Fetches 50+ analyst ratings per stock from Financial Modeling Prep `/grade/{symbol}` endpoint
   - Attempts to collect data from additional endpoints (price targets, estimates, consensus)
   - Implements robust error handling for empty/limited API responses
   - Processing time: ~2-3 seconds per stock for comprehensive analysis

2. **Grade Change Analysis**:
   - Parses grade transitions (previousGrade → newGrade) for momentum detection
   - Implements sophisticated grade hierarchy mapping:
     ```python
     grade_hierarchy = {
         'strong sell': 1, 'sell': 2, 'underweight': 2,
         'hold': 3, 'neutral': 3, 'equal weight': 3,
         'buy': 4, 'overweight': 4,
         'strong buy': 5, 'outperform': 4
     }
     ```
   - Calculates upgrade/downgrade ratios over 90-day lookback periods
   - Weights recent changes more heavily than historical baseline

3. **Multi-Factor Scoring System**:
   - **Rating Changes (30%)**: Primary momentum indicator from grade transitions
   - **Price Targets (25%)**: Target revision analysis (limited data on current tier)
   - **Estimate Revisions (20%)**: Earnings estimate momentum (limited data availability)
   - **Consensus Strength (15%)**: Analyst agreement and conviction measures
   - **Coverage Quality (10%)**: Active analyst participation and institutional coverage

4. **Quality Assurance and Validation**:
   - Filters out stocks with insufficient analyst coverage (< 5 ratings minimum)
   - Handles missing data gracefully with component-level fallbacks
   - Validates grade hierarchy consistency across different analyst firms
   - Generates detailed reasoning for each scoring component

5. **Output Generation**:
   - Produces 0-100 point scores with component breakdowns
   - Example output: "Rating=73.0, Target=0.0, Estimate=0.0, Consensus=0.0, Coverage=50.0, Final=26.9"
   - Includes comprehensive reasoning: "Strong analyst grade momentum with 73% positive rating changes"
   - Integrates with standard screening output format for consistency

**Performance Characteristics**:
- **API Efficiency**: Leverages working grade endpoint while gracefully handling limited endpoints
- **Data Quality**: Processes 100+ analyst rating records for comprehensive sentiment analysis
- **Scalability**: Individual stock processing allows for parallel execution when needed
- **Error Resilience**: Continues processing pipeline even when auxiliary endpoints fail

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

## Universe Data Sources

The pipeline supports multiple stock universes that are fetched from different sources.

### S&P 500 Universe

S&P 500 constituents are retrieved from Wikipedia:

```python
def get_sp500_symbols():
    """Get list of S&P 500 stocks from Wikipedia"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return df[['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry']]
```

### Russell 2000 Universe

Russell 2000 constituents are retrieved directly from iShares ETF holdings as a CSV download:

```python
def get_russell2000_symbols():
    """Get list of Russell 2000 stocks from iShares ETF holdings"""
    url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
    
    # Download the CSV file directly from iShares
    import requests
    import io

    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch Russell 2000 data: HTTP {response.status_code}")

    # Read the CSV content (skip header rows)
    df = pd.read_csv(io.StringIO(response.text), skiprows=9)
    
    # Extract and clean the relevant columns
    symbols_df = df[['Ticker', 'Name', 'Sector', 'Asset Class']]
    symbols_df = symbols_df.rename(columns={
        'Ticker': 'Symbol',
        'Name': 'Security',
        'Sector': 'GICS Sector'
    })
    
    # Filter for only equity securities
    symbols_df = symbols_df[symbols_df['Asset Class'] == 'Equity']
    
    return symbols_df
```

Important notes about Russell 2000 fetching:
- Downloads directly from iShares ETF holdings via CSV
- Uses `requests.get()` and `pd.read_csv()` with `io.StringIO()`
- No fallback to static CSV files or API data
- Typically returns around 2,000-2,100 symbols
- Properly handles column mapping to match S&P 500 format

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

## Expected Processing Outputs

**Recent Analyst Sentiment Results (November 2025)**:
- AAPL: Score 26.9/100 (Rating=73.0, Coverage=50.0, balanced analyst momentum)
- Typical S&P 500 coverage: 85%+ stocks have sufficient analyst data
- Processing efficiency: ~150 seconds for full S&P 500 universe analysis
- Grade data availability: 50+ analyst ratings per covered large-cap stock

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

## Data Quality Issues

### Financial Modeling Prep (FMP) Price-to-Book Ratio Issue

**Issue**: Financial Modeling Prep API returns `0` (integer) for `PriceToBookRatio` when the data is not available or cannot be calculated, rather than returning `null` or omitting the field.

**Impact**: This caused stocks with missing P/B ratio data to appear in price-to-book screening results with P/B = 0.00, creating false positives.

**Root Cause**: The API endpoints used by FMP (`key-metrics` and `ratios`) may return `0` for financial ratios when:
- The company doesn't have sufficient book value data
- The calculation results in an undefined or invalid ratio
- The data is temporarily unavailable

**Solution**: Updated the price-to-book screener to filter out stocks where `pb_ratio <= 0` instead of just `pb_ratio < 0`.

**Example Affected Stocks** (as of July 2025):
- BATRA (Atlanta Braves Holdings)
- SMID (Smith-Midland Corporation) 
- SENEA (Seneca Foods Corporation)
- MLAB (Mesa Laboratories)
- KG (Maiden Holdings)

**Fix Applied**: In `screeners/price_to_book.py`, changed the validation from:
```python
if pb_ratio is None or pb_ratio < 0 or np.isnan(float(pb_ratio)):
```
to:
```python
if pb_ratio is None or pb_ratio <= 0 or np.isnan(float(pb_ratio)):
```
