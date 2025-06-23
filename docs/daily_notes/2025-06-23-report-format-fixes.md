# Report Format Fixes - June 23, 2025

## Issue Fixed
Fixed a display issue in the screening report where the price-to-book strategy section was missing the P/B ratios column.

## Changes Made
1. Updated the `reporting.py` file to correctly display price-to-book values in the screening report:
   - Added support for 'price_to_book' column in the key metrics detection
   - Added P/B ratio to the summary section key metrics

2. The report now properly shows:
   - P/B ratio column in the price-to-book strategy table
   - P/B ratio in the summary section (e.g., "P/B: 0.43" for PARA)

## Testing
Verified the fix by:
1. Running the pipeline with the price-to-book strategy
2. Confirming the P/B ratios appear in the screening report
3. Verifying the summary section shows the correct P/B value for the top stock

## Technical Details
The issue occurred because the reporting.py file was looking for a 'pb_ratio' column, but the screener was storing the values in a 'price_to_book' column.

```python
# Before:
if 'pb_ratio' in results.columns:
    key_metrics.append('pb_ratio')
    
# After:
if 'pb_ratio' in results.columns:
    key_metrics.append('pb_ratio')
if 'price_to_book' in results.columns:
    key_metrics.append('price_to_book')
```

This fix maintains backward compatibility if any screeners use 'pb_ratio' while supporting the 'price_to_book' column used in the current implementation.

## Related Improvements
Also added support for price-to-book in the summary section key metrics detection:

```python
elif 'price_to_book' in results.columns:
    key_metric = f"P/B: {results.iloc[0]['price_to_book']:.2f}"
```

This ensures a consistent display format across all reports.
