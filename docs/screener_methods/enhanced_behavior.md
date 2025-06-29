# Screener Methods Documentation

## Enhanced Screener Behavior

As of June 2025, all screeners in the stock pipeline have been updated to follow a consistent pattern:

1. **Full Results With Threshold Flag**:
   - All screeners return **all** stocks with valid metrics, not just those meeting thresholds
   - Each result includes a `meets_threshold` flag to indicate stocks meeting original criteria
   - Results are always sorted by the primary metric (lowest P/E ratio first, etc.)

2. **Usage in Individual Mode**:
   ```python
   from screeners import screen_for_pe_ratio
   
   # Get all stocks with valid P/E ratios, sorted from lowest to highest
   results = screen_for_pe_ratio(universe_df)
   
   # To get only stocks meeting the threshold:
   filtered = results[results['meets_threshold'] == True]
   ```

3. **Usage in Combined Screener**:
   ```python
   from screeners import screen_for_combined
   
   # Combines PE, Price-to-Book and PEG ratio screeners by default
   results = screen_for_combined(universe_df)
   
   # Or specify which screeners to combine
   results = screen_for_combined(universe_df, strategies=['pe_ratio', 'peg_ratio'])
   ```

4. **Display Logic in main.py**:
   - For individual screeners: Displays stocks meeting thresholds when enough exist
   - Falls back to top N stocks when fewer meet thresholds
   - For combined screener: Always shows top ranked stocks across all strategies

This approach allows for more flexible filtering, better comparison across screeners,
and comprehensive ranking in the combined screener that takes all stocks into account.
