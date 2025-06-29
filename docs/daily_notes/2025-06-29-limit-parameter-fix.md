# Limit Parameter Fix - 2025-06-29

## Issue Fixed
Today I fixed the behavior of the `--limit` parameter in the main pipeline. Previously, `--limit` was reducing the size of the universe being analyzed, which led to several issues:

1. Fewer stocks were actually being analyzed than expected
2. The combined screener rankings were less accurate because they were based on a smaller universe
3. Results were less comprehensive since potentially good candidates could be excluded

## Changes Made

1. **Updated `--limit` Behavior**:
   - Now only affects the number of results displayed in output
   - Does not limit the stocks analyzed from the universe
   - All screeners always run on the full universe

2. **Updated Help Text**:
   - Changed from "Limit the number of stocks processed" to "Limit the number of stocks displayed in results"
   - Made the purpose clearer to users

3. **Modified Summary Output**:
   - When `--limit` is specified, summary shows: "Universe: sp500 (503 stocks, displaying top 20 for each strategy)"
   - Makes it clear that the analysis is still run on the full universe

## Benefits

1. **More Accurate Rankings**:
   - Combined screener now ranks all stocks, not just a subset
   - Individual screeners consider the full universe of stocks

2. **Better Performance Management**:
   - Users can still get quick output for testing by limiting display output
   - Full analysis still runs in the background

3. **Improved Consistency**:
   - Results are now consistent regardless of the display limit
   - Rankings are based on the full data set

## Usage Examples

```powershell
# Full analysis, but only show top 20 results per screener
python main.py --universe sp500 --limit 20 --strategies pe_ratio,price_to_book,combined

# Full analysis with full output (could be hundreds of stocks per screener)
python main.py --universe sp500 --strategies pe_ratio,price_to_book,combined
```
