# 2025-06-24: Turnaround Companies Screener

## New Screener Implementation: Companies That Have "Turned the Corner"

Today I implemented a new screener for identifying companies that have "turned the corner" or show signs of financial improvement. This screener addresses a crucial investing strategy: finding companies transitioning from financial stress to recovery.

### Key Detection Metrics

The screener looks for:

1. **EPS Trend Reversals**: 
   - Negative to positive EPS transitions
   - Sequential quarterly EPS improvement

2. **Revenue Momentum**:
   - Revenue growth reacceleration
   - Improving YoY growth rates

3. **Margin Expansion**:
   - Improving gross profit margins
   - Better operational efficiency

4. **Balance Sheet Strengthening**:
   - Growing cash reserves
   - Declining debt levels

### Scoring System

The screener uses a weighted scoring approach:
- EPS improvement: 3 points
- Revenue reacceleration: 2 points
- Margin improvements: 2 points
- Cash position improvement: 1 point
- Debt reduction: 1 point

Companies scoring 3+ points are included in results, sorted by total score.

### Usage

To run just the turnaround screener:

```python
from universe import get_stock_universe
from screeners import screen_for_turnaround_candidates

universe = get_stock_universe('sp500')
turnaround_candidates = screen_for_turnaround_candidates(universe)
print(f"Found {len(turnaround_candidates)} potential turnaround candidates")
```

### Future Enhancements

Potential improvements for future iterations:

1. **Analyst Estimate Revisions**: Add tracking of analyst estimate revisions, which can be leading indicators of improvement

2. **Technical Confirmation**: Incorporate technical indicators like golden crosses or volume trends to confirm fundamental improvements

3. **Short Interest Dynamics**: Add analysis of declining short interest, which can signal improving investor sentiment

4. **Sector-Relative Performance**: Compare company performance against sector peers to find outperformers

5. **Insider Buying**: Add detection of increased insider buying, a strong signal of management confidence

6. **Debt Refinancing Success**: Track successful debt refinancing events which can improve company financial health
