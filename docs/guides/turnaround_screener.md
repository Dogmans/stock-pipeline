# Legacy turnaround screener

`screen_for_turnaround_candidates` exists in its module but is not registered as a CLI strategy or visual flow box.

```python
from screeners.turnaround_candidates import screen_for_turnaround_candidates
from universe import get_stock_universe
results = screen_for_turnaround_candidates(get_stock_universe('russell2000'))
if not results.empty:
    passing = results.loc[results['meets_threshold'].eq(True)]
    print(passing[['symbol', 'company_name', 'primary_factor', 'turnaround_score']])
```

The function fetches quarterly income and balance sheets through the existing FMP provider. Its minimum income-history count follows `ScreeningThresholds.QUARTERS_RETURNED` (currently six), not a guaranteed eight-quarter history.

| Signal | Points |
| --- | --- |
| Negative-to-positive EPS | 5 |
| Continuous EPS improvement | 2 |
| Revenue recovery after decline | 4 |
| Revenue acceleration alternative | 2 |
| Margin recovery after compression | 3 |
| Cash recovery | 2 |
| Debt reduction | 2 |

Pass threshold is at least 5. Returned scored rows include `meets_threshold`; filter it before counting candidates. Missing overview or insufficient statements can omit input symbols. Signal alternatives are evaluated by the implementation, not all added indiscriminately.

The legacy `force_refresh` path uses old cache-invalidation calls; do not rely on it for scoped refresh. See [current cache semantics](../cache_usage.md). To export, create the destination directory before `to_csv()`.

[Current registered screens](../screener_methods.md), [focused tests](../testing/turnaround_screener_testing.md).
