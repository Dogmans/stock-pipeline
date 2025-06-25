# Unicode Character Replacement in Screener Output

Date: 2025-06-25

## Change Description

Instead of replacing Unicode characters at output time, we've modified the screener to use ASCII characters from the start. This is a more robust solution that prevents encoding issues entirely.

## Changes Made

1. Updated the turnaround screener in `screeners.py` to use "negative-to-positive EPS" instead of "negative→positive EPS"
2. Modified the EPS trend text to use "Negative-to-Positive EPS" instead of "Negative→Positive EPS"
3. Removed the character replacement code from `main.py` since it's no longer needed
4. Updated the corresponding test in `test_turnaround_screener_logic.py`

## Benefits

- Prevents Unicode encoding errors on Windows and other platforms with limited console encoding support
- More consistent approach by avoiding problematic characters from the start
- Eliminates the need for character replacement logic at output time
- Ensures compatibility across different environments and terminals

## Related Files

- `screeners.py` - Changed Unicode arrows to ASCII text
- `main.py` - Removed Unicode character replacement code
- `tests/test_turnaround_screener_logic.py` - Updated test expectations

## Testing

The changes were tested by:
- Verifying the modified files have correct syntax
- Ensuring the test case was updated properly
