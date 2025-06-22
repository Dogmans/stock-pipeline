# Screener Parameter Update - 2025-06-22

## Changes Made

Today we updated all screener functions to make the `universe_df` parameter required rather than optional, and to use it directly for stock selection.

### Key Changes:

1. Modified all screener functions in `screeners.py` to make `universe_df` a required parameter (no default):
   - `screen_for_price_to_book(universe_df, max_pb_ratio=None)`
   - `screen_for_pe_ratio(universe_df, max_pe=None)`
   - `screen_for_52_week_lows(universe_df, min_pct_off_high=None, max_pct_above_low=None)`
   - `screen_for_fallen_ipos(universe_df, max_years_since_ipo=3, min_pct_off_high=70)`
   - `screen_for_cash_rich_biotech(universe_df, min_cash_to_mc_ratio=None)`
   - `screen_for_sector_corrections(universe_df, **kwargs)`
   - `screen_for_combined(universe_df)`

2. Updated all screeners to use the `universe_df` parameter directly for stock selection, rather than calling `get_stock_universe(universe_df)`:
   ```python
   # Old approach:
   stocks = get_stock_universe(universe_df)
   symbols = stocks['symbol'].tolist()
   
   # New approach:
   symbols = universe_df['symbol'].tolist()
   ```

3. Fixed sector-specific code to use `universe_df` directly:
   ```python
   # Old approach:
   stocks = get_stock_universe(universe_df)
   biotech_stocks = stocks[stocks['gics_sector'] == 'Health Care']
   
   # New approach:
   biotech_stocks = universe_df[universe_df['gics_sector'] == 'Health Care']
   ```

4. Fixed usage examples in documentation to show that `universe_df` is now required.

### Rationale:

This change was made to:
1. Make it explicit that a universe DataFrame is required for all screeners
2. Remove the incorrect usage of `get_stock_universe(universe_df)` which was treating a DataFrame as a string universe name
3. Improve code clarity by directly using the provided `universe_df` parameter

### Testing:

Verified the module imports without errors and the entire pipeline still works with these changes.

## Next Steps

- Consider adding parameter type checking to validate that `universe_df` is actually a DataFrame with required columns
- Update any documentation that might reference the old parameter defaults
