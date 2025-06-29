# Combined Screener Documentation

The Combined Screener ranks stocks based on their pe### Limitations

- Different screeners may have very different total result counts, affecting rank comparisons
- Only includes stocks that appear in ALL selected screeners
- If no stocks appear in all screeners, the combined screener will return an empty result
- May exclude good candidates that are missing just one metric or data point
- Rankings are relative rather than absolute (e.g., #1 in one screener may be more impressive than #1 in another)

### Why Some Stocks May Not Appear in All Screeners

1. **Data Availability**: Each screener requires specific financial data (P/E ratio, PEG ratio, etc.). If a stock is missing data required by a screener, it will be excluded.

2. **Screening Criteria**: Each screener has its own filtering criteria. For example:
   - The PE ratio screener only includes stocks with PE ratio <= 10
   - The price-to-book screener only includes stocks with P/B ratio <= 1.2
   - The PEG ratio screener has its own criteria for identifying favorable growth at reasonable prices

3. **Data Quality**: Some stocks may have incomplete or unreliable data for certain metrics.

4. **Edge Cases**: Stocks with special situations (recent IPOs, negative earnings, etc.) may be ineligible for certain screeners.

### Example Analysis

When analyzing the SP500 universe with PE ratio, price-to-book, and PEG ratio screeners:

- PE ratio screener found 477 stocks (missing 26 stocks due to negative or missing P/E)
- Price-to-book screener found 471 stocks (missing 32 stocks with P/B > 1.2)
- PEG ratio screener found 258 stocks (missing 245 stocks that don't meet growth criteria)

Distribution analysis:
- 13 stocks appeared in PE ratio screener only
- 23 stocks appeared in P/B screener only
- 0 stocks appeared in PEG screener only (PEG requires positive earnings)
- 206 stocks appeared in both PE & P/B but not PEG
- 16 stocks appeared in both PE & PEG but not P/B
- 0 stocks appeared in both P/B & PEG but not PE
- 242 stocks appeared in ALL screeners

This explains why the combined screener only shows a subset of the full universe.nce across multiple screening criteria, identifying companies that score well across various fundamental and technical factors.

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
3. Only include stocks that appear in ALL specified screeners
4. For each qualifying stock:
   - Calculate the average rank position
   - Record which screeners it appeared in
   - Store key metrics from each screener
5. Sort the final results by average rank

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

- Different screeners may have very different total result counts, affecting rank comparisons
- Simple weighting system that slightly favors stocks appearing in multiple screeners
- May undervalue stocks that excel extremely in just one category
- Rankings are relative rather than absolute (e.g., #1 in one screener may be more impressive than #1 in another)
