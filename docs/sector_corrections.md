# Legacy sector correction helper

The function `screen_for_sector_corrections` in `screeners/sector_corrections.py` is not a registered CLI strategy or editor box.

```python
from screeners.sector_corrections import screen_for_sector_corrections
from universe import get_stock_universe
results = screen_for_sector_corrections(get_stock_universe('sp500'), threshold=-10)
```

It filters the market sector-performance table's `performance` values at or below the threshold and maps candidate stocks to affected sectors. When sectors qualify but stock mapping produces no rows, it can return sector ETF rows as fallback evidence. Inspect the result's actual sector/status fields before using it as an operating-company shortlist. An empty result can also reflect missing upstream data.

The helper's comments mention correction from highs, but its gate uses the supplied sector-performance metric; do not assume a distinct drawdown calculation. Existing reports can consume compatible rows programmatically. [Registered screens](screener_methods.md), [data processing](data_processing.md).
