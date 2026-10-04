# Screener package structure

Current screens are `BaseScreener` subclasses explicitly registered in `utils/screener_registry.py`. The registry is lazy-initialized; adding a Python module does not automatically discover it. The editor catalog derives constructor parameters and default-rule descriptions through `workflow.py`.

```python
from utils import get_screener, run_screener
from universe import get_stock_universe
universe_df = get_stock_universe('sp500')
results = run_screener('pe_ratio', universe_df, max_pe=15)
passing = results.loc[results['meets_threshold'].eq(True)] if not results.empty else results
```

`screeners/__init__.py` exports selected classes, not all historical function wrappers. Import legacy functions from their module, such as `screeners.turnaround_candidates`. `screeners/utils.py` and function-based combined screeners use a separate legacy discovery path.

## Adding a screen

1. Subclass `BaseScreener` in `screeners/` and implement its abstract interface.
2. Register the class in `auto_register_screeners()`.
3. Expose simple numeric/text constructor settings; the editor validates and displays these.
4. Describe its actual pass condition in the workflow catalog; preserve sort direction.
5. Keep missing data distinct from failed eligibility and test meaningful boundaries.
6. Update the strategy table, examples and [offline test suite](../testing.md).

The base implementation fetches company overview per symbol, skips absent/invalid scores and emits scored rows with threshold flags. Override `screen_stocks()` for stronger auditing requirements. TAM evaluates all hard checks separately, overrides the base path, and keeps a research-priority score that cannot bypass eligibility. `opt_in` prevents automatic inclusion in default screen sets.

[Architecture](../../DOCUMENTATION.md), [strategy reference](../screener_methods.md).
