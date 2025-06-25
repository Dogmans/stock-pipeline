# Turnaround Screener User Guide

## Quick Start

To run the turnaround screener against the S&P 500 universe:

### In PowerShell

```powershell
cd C:\Programs\stock_pipeline
python -c "from screeners import screen_for_turnaround_candidates; import universe; results = screen_for_turnaround_candidates(universe.get_sp500_universe()); print(f'Found {len(results)} turnaround candidates'); print(results[['symbol', 'name', 'primary_factor', 'turnaround_score']])"
```

### Using Tasks

Run the Value Pipeline task (which includes the turnaround screener):

```
Run task: "Run Value Pipeline"
```

### Output Format

The screener will generate results in this format:

```
Found 3 turnaround candidates
  symbol         name          primary_factor  turnaround_score
0    XYZ  XYZ Company     Negative→Positive EPS               7
1    ABC  ABC Company           Cash Recovery               6
2    DEF  DEF Company          Revenue Recovery               5
```

## Advanced Usage

### Force Refresh Data

To bypass the cache and fetch fresh data:

```python
from screeners import screen_for_turnaround_candidates
import universe

# Force fresh data
results = screen_for_turnaround_candidates(universe.get_sp500_universe(), force_refresh=True)
```

### Save Results to CSV

```python
from screeners import screen_for_turnaround_candidates
import universe

results = screen_for_turnaround_candidates(universe.get_sp500_universe())
if not results.empty:
    results.to_csv('output/turnaround_analysis/turnaround_candidates.csv', index=False)
    print(f"Saved {len(results)} candidates to CSV")
```

### Custom Analysis

```python
from screeners import screen_for_turnaround_candidates
import universe
import pandas as pd
import matplotlib.pyplot as plt

# Run screener
results = screen_for_turnaround_candidates(universe.get_sp500_universe())

# Analysis by sector
if not results.empty:
    sector_counts = results['sector'].value_counts()
    print("\nSector Distribution:")
    print(sector_counts)
    
    # Plot sector distribution
    plt.figure(figsize=(12, 6))
    sector_counts.plot(kind='bar')
    plt.title('Turnaround Candidates by Sector')
    plt.tight_layout()
    plt.savefig('output/charts/turnaround_sectors.png')
```

## Understanding the Scoring System

Candidates are scored based on:

1. **EPS Trend** (0-3 points)
   - Negative→Positive transition: 3 points
   - Strong improvement (>50%): 2 points

2. **Revenue Trend** (0-2 points)
   - Recovery from decline to growth: 2 points

3. **Margin Trend** (0-2 points)
   - Recovery after bottoming (>10% improvement): 2 points

4. **Balance Sheet** (0-4 points)
   - Cash recovery: 2 points
   - Debt reduction: 2 points

Only stocks with a total score ≥ 5 are flagged as turnaround candidates.

## Common Issues

1. **No Candidates Found**
   - This is often expected! True turnarounds are rare, especially in the S&P 500
   - Try other universes like Russell 2000 for more potential candidates
   - Check if `force_refresh=True` provides different results

2. **Missing Financial Data**
   - Some companies may lack sufficient historical data
   - Ensure your data provider API keys are valid
   - Check rate limits if many requests fail

## Related Documentation

- [Data Processing Patterns](data_processing.md)
- [Provider Guides](provider_guides.md)
- [Complete Screener Methods](screener_methods.md)
