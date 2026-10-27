# Legacy combined helpers

These helpers in `screeners/combined.py` are programmatic functions, not current registered CLI strategies or grouped editor nodes.

`run_screeners_with_registry(universe_df, screener_names=None, **screener_kwargs)` runs class-registry screens and returns a dictionary of result DataFrames. Its default set excludes TAM and the four opt-in profitability screens. It does not create an average-rank composite.

`screen_for_combined(universe_df=None, strategies=None, combination_name=None)` calls legacy `screen_for_<strategy>` functions, ranks their returned rows and retains symbols returned by every requested strategy. Lower average rank is better. It does not filter each component by `meets_threshold`, so intersection membership must not be described as passing every hard threshold. There is no partial-intersection fallback.

```python
from screeners.combined import screen_for_combined
from universe import get_stock_universe
results = screen_for_combined(get_stock_universe('sp500'), strategies=['pe_ratio', 'peg_ratio'])
```

Default legacy combination is `traditional_value` (P/E, P/B, PEG). Other configurations are `high_performance`, `comprehensive`, and `distressed_value` in `config.CombinedScreeners`. Some configuration names do not match available legacy wrappers; missing components are logged and can prevent an intersection. They are retained legacy code, not guaranteed supported CLI presets.

Use `composite_score` for the registered numeric multi-factor screen. Use saved workflow JSON for sequential routing. Use the single TAM box for auditable broad quantitative discovery; it is neither the legacy combined helper nor a theme classifier.
