# PEG Ratio Screener Documentation

The PEG (Price/Earnings to Growth) ratio screener identifies stocks that may be undervalued relative to their growth rates.

## Overview

The PEG ratio is calculated as:
```
PEG Ratio = P/E Ratio / Expected Annual Growth Rate (%)
```

A PEG ratio below 1.0 generally indicates that a stock may be undervalued relative to its expected growth rate.

## Implementation Details

### Function Arguments

- `universe_df`: DataFrame containing the stock universe
- `max_peg_ratio`: Maximum PEG ratio to include (default: 1.0)
- `min_growth`: Minimum expected growth rate percentage (default: 5.0%)
- `force_refresh`: Whether to force refresh data from API

### Data Sources

The screener uses the following data:
1. P/E Ratio from company overview data
2. Growth rates calculated from:
   - Quarterly EPS data (preferred method, looks at YoY growth)
   - Annual EPS growth rate from company overview
   - Revenue growth rate if EPS growth is not available

### Calculation Method

1. Calculate P/E ratio from company overview data
2. Calculate growth rate:
   - First attempt: Calculate YoY EPS growth from quarterly financial statements
   - Second attempt: Use EPS growth from company overview 
   - Third attempt: Use revenue growth from company overview
3. Calculate PEG ratio = P/E ratio / Growth Rate
4. Filter for stocks with PEG ratio <= max_peg_ratio and growth rate >= min_growth

### Output Fields

The resulting DataFrame contains these columns:
- symbol
- company_name
- sector
- pe_ratio
- growth_rate
- growth_type (EPS YoY, EPS, or Revenue)
- peg_ratio
- market_cap
- reason (formatted explanation)

## Usage Examples

### Basic Usage

```python
from screeners import screen_for_peg_ratio
from universe import get_sp500_universe

# Get SP500 stocks with PEG ratio under 1.0
results = screen_for_peg_ratio(get_sp500_universe())

# Display results
print(results[['symbol', 'company_name', 'peg_ratio', 'pe_ratio', 'growth_rate', 'growth_type']])
```

### Custom Parameters

```python
# Find stocks with very low PEG ratios (under 0.5) and reasonable growth (over 10%)
results = screen_for_peg_ratio(
    universe_df=get_sp500_universe(),
    max_peg_ratio=0.5,
    min_growth=10.0,
    force_refresh=False
)
```

## Interpretation

- **PEG < 0.5**: Potentially significantly undervalued relative to growth
- **PEG 0.5-1.0**: Potentially moderately undervalued relative to growth
- **PEG 1.0-1.5**: Fairly valued relative to growth
- **PEG > 1.5**: Potentially overvalued relative to growth

## Limitations

- Growth projections are based on historical data and may not represent future growth
- Unusually high growth rates can artificially lower the PEG ratio
- Does not account for industry differences where certain sectors typically have higher growth
- Negative P/E ratios (companies with losses) cannot produce meaningful PEG ratios
