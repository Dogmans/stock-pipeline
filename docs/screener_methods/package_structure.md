# Screeners Package Structure

The stock screening pipeline uses a modular screener architecture with each screener encapsulated in its own module within the `screeners` package.

## Package Organization

- `screeners/__init__.py`: Aggregates and exports all screeners for backwards compatibility
- `screeners/utils.py`: Contains utility functions like `get_available_screeners()` and `run_all_screeners()`
- `screeners/common.py`: Shared imports and setup code used by all screener modules

## Available Screeners

| Module | Function | Description |
|--------|----------|-------------|
| `pe_ratio.py` | `screen_for_pe_ratio()` | Screens for stocks with low P/E ratios |
| `price_to_book.py` | `screen_for_price_to_book()` | Screens for stocks trading near or below book value |
| `fifty_two_week_lows.py` | `screen_for_52_week_lows()` | Screens for stocks near their 52-week lows |
| `fallen_ipos.py` | `screen_for_fallen_ipos()` | Screens for IPOs that have dropped significantly from their highs |
| `turnaround_candidates.py` | `screen_for_turnaround_candidates()` | Screens for stocks showing signs of financial turnaround |
| `peg_ratio.py` | `screen_for_peg_ratio()` | Screens for stocks with attractive PEG (Price/Earnings to Growth) ratios |
| `sector_corrections.py` | `screen_for_sector_corrections()` | Screens for stocks in sectors that are in correction |
| `combined.py` | `screen_for_combined()` | Runs multiple screeners and combines results based on average ranking |

## Usage

You can use the screeners in two ways:

### Direct module import:

```python
from screeners.pe_ratio import screen_for_pe_ratio

results = screen_for_pe_ratio(universe_df)
```

### Through the package:

```python
from screeners import screen_for_pe_ratio, run_all_screeners, get_available_screeners

# Run a specific screener
results = screen_for_pe_ratio(universe_df)

# Get list of available screeners
available_screeners = get_available_screeners()

# Run all screeners
all_results = run_all_screeners(universe_df)
```

## Screener Implementation

Each screener follows a standard interface:

```python
def screen_for_xxx(universe_df, **kwargs):
    """
    Screen for stocks based on xxx criteria.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        **kwargs: Additional parameters specific to this screener
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    # Implementation
    ...
    
    return results_df
```

## Adding New Screeners

To add a new screener:

1. Create a new module in the `screeners` package (e.g., `screeners/my_new_screener.py`)
2. Implement the `screen_for_xxx` function following the standard interface
3. Update `__init__.py` to import and expose the new screener
4. Update `utils.py` to include the new screener in `get_available_screeners()`
