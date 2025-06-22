# Sector Correction Screener Updates

## Overview
The sector correction screener now returns stocks that are in sectors experiencing a correction, rather than just returning sector-level data. This makes it consistent with other screeners and ensures proper integration with the reporting system.

## Implementation Details

### Return Values
- The screener now returns a DataFrame containing stocks that belong to sectors in correction
- Each stock row includes:
  - Standard stock information (symbol, name, sector, etc.)
  - Sector performance metrics (1-month change, 3-month change)
  - Sector status flag (Correction or Bear Market)

### Fallback Logic
If no stocks are found but sectors are in correction, the screener creates a DataFrame with sector ETF entries as a fallback. This ensures that the reporting system can still show which sectors are in correction, even if specific stocks aren't available.

## Using the Screener
```python
# Basic usage
universe_df = get_stock_universe("sp500")  # Required parameter
sector_corrections = screen_for_sector_corrections(universe_df)

# Access stocks in correcting sectors
if not sector_corrections.empty:
    # Get unique sectors in correction
    unique_sectors = sector_corrections['sector'].unique()
    
    # Filter for most severely impacted sectors (bear market)
    bear_market_stocks = sector_corrections[sector_corrections['sector_status'] == 'Bear Market']
    
    # Find stocks with the largest correction
    worst_performing = sector_corrections.sort_values('sector_1m_change').head(10)
```

## Integration with Reporting
The screener now properly integrates with the reporting system because:
1. It returns stocks with a 'symbol' column like other screeners
2. It includes sector performance data for each stock
3. It properly reports the number of stocks and sectors in correction

## Common Issues
- If the screener returns an empty DataFrame, it means no sectors are currently in correction
- If the screener returns sector ETFs instead of stocks, it means sectors are in correction but no specific stocks could be identified
