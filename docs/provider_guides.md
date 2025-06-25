# Data Provider Guides

## Provider-Specific Documentation

- [Financial Modeling Prep API Guide](provider_guides/financial_modeling_prep.md) - Complete guide to our FMP API integration

## Provider API Caching Guide

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

# Direct Provider Access in Screeners

## Architecture Overview

As of November 2023, we've adopted a direct access architecture where:

1. Each screener is responsible for fetching its own data directly from the provider
2. Only the stock universe is passed from main.py to the screeners
3. No centralized data processing or chunked processing is used

## Standard Screener Pattern

All screeners now follow this pattern:

```python
def screen_for_example(universe_df=None, config_param=None):
    """
    Screen for stocks based on some criteria.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        config_param: Configuration parameter
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    # Import the provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Get stock universe
    stocks = get_stock_universe(universe_df)
    symbols = stocks['symbol'].tolist()
    
    # Initialize the provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in symbols:
        try:
            # Get necessary data from provider
            data = fmp_provider.get_some_data(symbol)
            
            # Apply screening logic
            if meets_criteria(data):
                results.append({
                    'symbol': symbol,
                    'some_metric': value,
                    'reason': "Meets criteria because..."
                })
                
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            # Stop execution if provider fails
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        return pd.DataFrame(results)
    else:
        return pd.DataFrame()
```

## Error Handling

When a provider fails to return data, the screener should raise an exception to stop execution:

```python
try:
    data = fmp_provider.get_some_data(symbol)
    # Process data
except Exception as e:
    logger.error(f"Error fetching data for {symbol}: {e}")
    # Stop execution if provider fails
    raise Exception(f"Data provider failed for symbol {symbol}: {e}")
```

# Financial Modeling Prep API Usage Guide

## API Overview
Financial Modeling Prep (FMP) is our primary data provider for financial data. This guide documents the key functions and their usage patterns.

## FMP Provider Methods

### Historical Price Data
```python
provider = FinancialModelingPrepProvider()
price_data = provider.get_historical_prices(['AAPL', 'MSFT'], period='1y', interval='1d')
```

The `get_historical_prices` method returns a dictionary where:
- Keys are stock symbols
- Values are DataFrames with columns: `Open`, `High`, `Low`, `Close`, `Volume`

### Company Overview
```python
provider = FinancialModelingPrepProvider()
overview = provider.get_company_overview('AAPL')
```

Returns a dictionary with company information including:
- Symbol, Name, Description
- Market capitalization, PE ratio, EPS 
- 52-week high/low
- Price-to-book ratio, price-to-sales ratio
- Return on equity, return on assets
- Profit margin, operating margin
- Debt-to-equity ratio, EV to EBITDA

### Income Statement
```python
provider = FinancialModelingPrepProvider()
income_statement = provider.get_income_statement('AAPL', annual=True)
```

Returns a DataFrame containing income statement data with columns like:
- fiscalDateEnding
- totalRevenue, costOfRevenue, grossProfit
- operatingExpenses, operatingIncome
- netIncome, ebitda

### Balance Sheet
```python
provider = FinancialModelingPrepProvider()
balance_sheet = provider.get_balance_sheet('AAPL', annual=True)
```

Returns a DataFrame containing balance sheet data with columns like:
- fiscalDateEnding
- totalAssets, totalCurrentAssets
- totalLiabilities, totalCurrentLiabilities
- totalShareholderEquity, cash, shortTermInvestments
- longTermDebt, commonStock

### Cash Flow
```python
provider = FinancialModelingPrepProvider()
cash_flow = provider.get_cash_flow('AAPL', annual=True)
```

Returns a DataFrame containing cash flow data with columns like:
- fiscalDateEnding
- operatingCashflow, capitalExpenditures
- freeCashflow, dividendPayout
- changeInCash, repurchaseOfStock, issuanceOfStock

## Error Handling
All methods will return an empty DataFrame or dictionary on error, logging the error details.

## Caching
All methods use the cache system, which persists results to disk for:
- Company overview (24 hours)
- Historical prices (24 hours)
- Financial statements (1 week)

## Rate Limiting
FMP rate limiting is managed through the `RateLimiter` class which prevents exceeding API rate limits.

## Annual vs Quarterly Data
To get quarterly financial data (income statement, balance sheet, cash flow) instead of annual data:

```python
# Get quarterly income statement
quarterly_income_statement = provider.get_income_statement('AAPL', annual=False)

# Get quarterly balance sheet
quarterly_balance_sheet = provider.get_balance_sheet('AAPL', annual=False)

# Get quarterly cash flow statement
quarterly_cash_flow = provider.get_cash_flow('AAPL', annual=False)
```

**Important:** Always use the `annual=False` parameter to get quarterly data. Do not use `period="quarter"` as this is not supported by the API methods. The methods handle the period parameter internally.

## Usage in Screeners
When implementing a screener:
1. Initialize the provider
2. Fetch only the data needed for that specific screener
3. Handle any errors that occur during data retrieval
4. Use the returned data for screening logic

Example:
```python
def my_screener(universe_df):
    provider = FinancialModelingPrepProvider()
    symbols = universe_df['symbol'].tolist()
    results = []
    
    for symbol in symbols:
        try:
            overview = provider.get_company_overview(symbol)
            if not overview:
                continue
                
            # Your screening logic here
            if overview['PERatio'] < 15:
                results.append({
                    'symbol': symbol,
                    'pe_ratio': overview['PERatio']
                    # Additional data
                })
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            
    return pd.DataFrame(results) if results else pd.DataFrame()
```

# API-Specific Method Naming (June 2025 Update)

As of June 2025, we've updated our provider architecture to allow each provider to use method names that match their specific APIs rather than conforming to a common interface. This results in clearer, more maintainable code that better reflects each API's capabilities.

## Example of Provider-Specific Methods

### Financial Modeling Prep Provider
```python
# Methods match FMP API endpoints
provider = FinancialModelingPrepProvider()

# Company profile information
profile = provider.get_company_profile(symbol)

# Financial statements
income = provider.get_income_statement_annual(symbol)
balance = provider.get_balance_sheet_quarterly(symbol)

# Stock quotes
quote = provider.get_quote(symbol)
```

### Alpha Vantage Provider
```python
# Methods match Alpha Vantage API functions
provider = AlphaVantageProvider()

# Company overview
overview = provider.get_company_overview(symbol)

# Time series data
daily = provider.get_time_series_daily(symbol)
intraday = provider.get_time_series_intraday(symbol, interval='5min')
```

## Common Utilities

All providers still extend the `BaseDataProvider` class, which provides these common utilities:

1. `parallel_data_fetcher` - For parallel data fetching using any method
2. `get_provider_name` - Returns the name of the provider
3. `get_provider_info` - Returns information about the provider's rate limits

## Provider Selection in Screeners

When writing screeners, you should:

1. Import the specific provider you need
2. Use the provider's API-specific methods
3. Refer to the provider's documentation for available methods

Example:
```python
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider

def screen_for_something(universe_df):
    # Initialize provider
    provider = FinancialModelingPrepProvider()
    
    # Use API-specific method names
    data = provider.get_company_profile(symbol)
```

# Financial Modeling Prep API Endpoints for Company Metrics

## Overview of Required Metrics and Source Endpoints

The company metrics needed for stock screening should be retrieved from specific endpoints of the Financial Modeling Prep API:

| Metric | Primary Endpoint | Fallback Endpoint | Parameter |
|--------|------------------|-------------------|-----------|
| MarketCapitalization | /market-capitalization | /profile | mktCap |
| PERatio | /quote | /ratios or /profile | pe |
| EPS | /quote | /key-metrics | eps |
| Beta | /profile | /company-outlook | beta |
| 52WeekHigh | /quote | /profile (range field) | yearHigh or range |
| 52WeekLow | /quote | /profile (range field) | yearLow or range |
| LastDividendDate | /profile | /historical-price-full/stock_dividend | lastDiv |
| PriceToBookRatio | /key-metrics | /ratios | priceToBookRatio |
| PriceToSalesRatio | /key-metrics | /ratios | priceToSalesRatio |

## Implementation Strategy

To ensure we have all required metrics, the `get_company_overview` method should:

1. Start with the `/profile` endpoint as the base information source
2. Supplement with data from `/quote` for latest market data including price, 52-week high/low
3. Add additional financial metrics from `/key-metrics` or `/ratios`
4. Use `/market-capitalization` for more accurate market cap values when needed

## Example Implementation Pattern

```python
def get_company_overview(self, symbol):
    """Get comprehensive company data from multiple endpoints"""
    # Get base profile
    profile_data = self._fetch_profile(symbol)
    if not profile_data:
        return {}
        
    # Initialize result with profile data
    overview = self._convert_profile_to_overview(profile_data)
    
    # Supplement with quote data for latest market metrics
    quote_data = self._fetch_quote(symbol)
    if quote_data:
        overview.update(self._extract_quote_metrics(quote_data))
    
    # Add additional financial ratios if missing
    if not overview.get('PERatio') or not overview.get('PriceToBookRatio'):
        ratio_data = self._fetch_ratios(symbol)
        if ratio_data:
            overview.update(self._extract_ratio_metrics(ratio_data))
    
    return overview
```

## Handling Missing Data

If certain endpoints fail or return incomplete data:

1. Log a warning but don't fail the entire operation
2. Attempt to get the data from fallback endpoints
3. Set missing metrics to None or empty string rather than failing
4. Include a "data_completeness" field to indicate completeness level

## Rate Limit Considerations

Different endpoints count against the same rate limits, so optimize calls:

- Batch related requests where possible
- Cache aggressively to avoid duplicate calls
- Use the most data-rich endpoints first (e.g., profile contains many fields)
- Only call additional endpoints when necessary fields are missing
