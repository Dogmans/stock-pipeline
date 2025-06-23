# Report Formatting Improvement - June 23, 2025

## Change Made
Updated the price-to-book ratio formatting in the screening report to use 3 decimal places instead of the default 2 decimal places, making values more precise and readable.

## Technical Changes
1. Modified `reporting.py` to specifically handle price-to-book values with 3 decimal places:
   - In the summary section: `f"P/B: {results.iloc[0]['price_to_book']:.3f}"`
   - In the detailed table: Special case for price-to-book values to use `.3f` format

2. Before and After Example:
   - Before: PARA P/B ratio shown as "0.43" (summary) and "0.425578431372549" (table)
   - After: PARA P/B ratio shown as "0.426" (summary) and "0.426" (table)

## Justification
Price-to-book ratios often require more precision than other financial ratios because small differences can be meaningful when evaluating stocks trading close to book value. The 3-decimal format provides:

1. Better precision than the default 2 decimals
2. More readable format compared to the full floating-point values
3. Consistency between the summary and detailed table

## Implementation Details
Added a special case in the metric formatting logic:

```python
# For summary section
if 'price_to_book' in results.columns:
    key_metric = f"P/B: {results.iloc[0]['price_to_book']:.3f}"
    
# For table rows
if metric == 'price_to_book':
    f.write(f" {row[metric]:.3f} |")
elif 'ratio' in metric:
    f.write(f" {row[metric]:.2f} |")
```

This change ensures that price-to-book values are consistently formatted across the report while maintaining the existing format for other ratio types.
