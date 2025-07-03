# Default Display Limits for Screeners - July 3, 2025

## Issue
When running individual (non-combined) screeners against the Russell 2000 universe, the output can be overwhelming with hundreds of matching stocks, making it difficult to review results.

## Solution
Added default display limits for screeners to manage output size:

1. Set the default `--limit` parameter to 20 (previously it was unlimited)
2. Maintained a smaller display limit (10) for the combined screener
3. Updated all parts of the code that handle display limits for consistency
4. Updated documentation to reflect these changes

## Implementation Details

### Changes to `main.py`

1. Updated command-line argument parser:
   ```python
   parser.add_argument('--limit', type=int, default=20,
                       help='Limit the number of stocks displayed in results (default: 20 for non-combined screeners)')
   ```

2. Modified display logic to use different defaults based on screener type:
   - Non-combined screeners: Default limit of 20
   - Combined screener: Default limit of 10 (unchanged)

3. Simplified conditional logic for applying display limits

## Documentation

Added documentation in `docs/powershell_commands.md`:
- Default display limits for each screener type
- Examples of using custom limits
- Information about why this change was made

## Rationale

This change helps manage the large volume of results from Russell 2000 screeners (which can return 4x as many results as S&P 500 screeners) while still providing enough data for analysis. Users can still see all results by specifying a larger limit or removing the limit entirely with `--limit 0`.

## Testing

Verified the changes with:
```powershell
# Test with default limit (should show 20 results)
python main.py --universe russell2000 --strategies pe_ratio

# Test with custom limit
python main.py --universe russell2000 --strategies pe_ratio --limit 5

# Test combined screener (should show max 10)
python main.py --universe russell2000 --strategies combined
```
