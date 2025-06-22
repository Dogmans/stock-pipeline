# Screener Architecture Refactoring (November 2023)

## Overview

In November 2023, we refactored the stock screening pipeline to implement a more modular and direct data access architecture. This document outlines the key changes and the rationale behind them.

## Architectural Changes

### Before

- Main gets stock universe
- Main pre-processes all data via central data processing functions
- Main passes processed data to each screener
- Screeners use this pre-processed data
- Chunked processing for large universes

### After

- Main gets stock universe
- Main passes universe directly to each screener
- Each screener fetches its own data directly from the provider
- No more chunked processing
- Each screener is fully self-contained and independent

## Benefits

1. **Simplicity**: Each screener is now fully self-contained with its own data fetching logic
2. **Efficiency**: Only the data needed for a specific screening strategy is fetched
3. **Maintainability**: Screeners can be updated independently without affecting others
4. **Error handling**: Clearer error propagation with failures isolated to specific screeners
5. **Testing**: Easier to mock and test individual screeners

## Implementation Details

### Standard Screener Pattern

```python
def screen_for_something(universe_df=None, config_param=None):
    """
    Screen for stocks based on specific criteria.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        config_param: Configuration parameter
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Get stock universe
    stocks = get_stock_universe(universe_df)
    symbols = stocks['symbol'].tolist()
    
    # Initialize the FMP provider
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
                    'metric': value,
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

### Main.py Changes

- Removed references to chunking
- Removed centralized data processing calls
- Only pass universe_df to run_all_screeners
- Simplified flow and dependencies

### Caching

The caching mechanism is maintained at the provider level, ensuring we don't make redundant API calls:

```python
@cache.memoize(expire=24*3600)  # 24 hours in seconds
def get_company_overview(self, symbol, force_refresh=False):
    if force_refresh:
        cache.delete(self.get_company_overview, symbol)
    # API call implementation here
```

## Testing

New tests have been added in `test_new_screeners.py` that verify:
1. Each screener can fetch its own data
2. Error handling works correctly
3. The overall pipeline with the new architecture functions properly

## Future Work

1. Consider further optimizations for providers that support batch API calls
2. Enhance error handling with more graceful fallbacks
3. Add more comprehensive testing for edge cases
