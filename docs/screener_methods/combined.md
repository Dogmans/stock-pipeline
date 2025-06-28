# Combined Screener Documentation

The Combined Screener ranks stocks based on their performance across multiple screening criteria, identifying companies that score well across various fundamental and technical factors.

## Overview

The Combined Screener:
1. Runs multiple individual screeners
2. Ranks stocks in each screener's result set
3. Calculates an average rank for stocks appearing in multiple screeners
4. Sorts the final output by average rank (lower is better)

This approach provides a more balanced view that doesn't overly favor any single metric.

## Implementation Details

### Function Arguments

- `universe_df`: DataFrame containing the stock universe
- `strategies`: List of screener strategies to combine (default: ['pe_ratio', 'price_to_book', 'peg_ratio'])
- `force_refresh`: Whether to force refresh data from API

### Algorithm

1. Run each individual screener in the strategies list
2. For each screener, assign rank positions (1 being the best) to all stocks
3. For each stock that appears in multiple screeners:
   - Calculate the average rank position
   - Record which screeners it appeared in
   - Store key metrics from each screener
4. Sort the final results by average rank

### Advantages

- **Balanced Approach**: Identifies stocks that are solid across multiple metrics rather than excellent in just one category
- **Reduces Outliers**: Less susceptible to data anomalies in any single metric
- **Customizable**: Can combine any set of screeners based on current market conditions or investment strategy

### Output Fields

The resulting DataFrame contains these columns:
- `symbol`: Stock ticker symbol
- `company_name`: Company name
- `sector`: Company sector
- `avg_rank`: Average rank position across all screeners (lower is better)
- `screener_count`: Number of screeners where the stock appeared
- `rank_details`: Individual rank in each screener (e.g., "pe_ratio: #3, price_to_book: #7")
- `metrics_summary`: Summary of key metrics from each screener
- `reason`: Formatted explanation with average rank and metrics

## Usage Examples

### Basic Usage

```python
from screeners import screen_for_combined
from universe import get_sp500_universe

# Get SP500 stocks that rank well across default screeners
results = screen_for_combined(get_sp500_universe())

# Display combined results
print(results[['symbol', 'company_name', 'avg_rank', 'metrics_summary']])
```

### Custom Screener Combination

```python
# Find stocks that rank well across value, growth, and turnaround metrics
results = screen_for_combined(
    universe_df=get_sp500_universe(),
    strategies=['pe_ratio', 'peg_ratio', 'price_to_book', 'turnaround_candidates'],
    force_refresh=False
)
```

### From Command Line

```powershell
python main.py --universe sp500 --strategies combined
```

## Interpretation

- **Lower average rank**: Better overall performance across screeners
- **Higher screener count**: More consistent performance across different metrics
- **Balanced metrics**: Look for stocks with reasonably good metrics across all categories rather than excellent in just one

## Limitations

- Requires stocks to appear in at least 2 screeners for more reliable rankings
- Different screeners may have very different total result counts, affecting rank comparisons
- No weighting of screeners (each screener has equal importance)
- May miss stocks that excel extremely in just one category
