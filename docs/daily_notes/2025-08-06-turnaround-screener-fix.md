# Turnaround Screener Fix - 2025-08-06

## Issues Fixed
Fixed parameter mismatch in the turnaround screener when calling Financial Modeling Prep provider methods.

## Changes Made
1. Updated `screeners.py` to use the correct parameter for requesting quarterly data:
   - Changed `get_income_statement(symbol, period="quarter", limit=8)` to `get_income_statement(symbol, annual=False, force_refresh=force_refresh)`
   - Changed `get_balance_sheet(symbol, period="quarter", limit=4)` to `get_balance_sheet(symbol, annual=False, force_refresh=force_refresh)`
2. Added missing `force_refresh` parameter to the `screen_for_turnaround_candidates` function signature:
   - Changed `def screen_for_turnaround_candidates(universe_df):` to `def screen_for_turnaround_candidates(universe_df, force_refresh=False):`

## Root Cause
The Financial Modeling Prep provider methods were designed to use `annual=False` to request quarterly data, not `period="quarter"`. The provider methods handle the period parameter internally based on the `annual` boolean parameter.

## Testing
After making the changes, the turnaround screener should work correctly without throwing parameter errors.

## Notes for Future Development
- When using the Financial Modeling Prep provider, always use `annual=False` for quarterly data and `annual=True` (default) for annual data.
- The `limit` parameter is handled internally in the provider, so there's no need to specify it when calling the provider methods.
- Ensure consistent interface usage across all data providers to avoid similar issues.
