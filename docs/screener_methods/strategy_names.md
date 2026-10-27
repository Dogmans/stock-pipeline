# Strategy names

The supported runtime registry is `utils/screener_registry.py`. Use its names exactly:

```python
from utils import list_screeners, get_screener, run_screener
print(list_screeners())
```

[The current strategy table](../screener_methods.md) lists all 20 names and defaults. `fifty_two_week_lows` and `fcf_yield` are registry IDs; `52_week_lows` and `free_cash_flow_yield` are not their CLI aliases. Historical `value`, `growth`, `book_value`, `combined`, `turnaround_candidates`, `fallen_ipos`, and `sector_corrections` are not registered CLI/editor IDs.

```powershell
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies pe_ratio,price_to_book,peg_ratio
.venv-ui\Scripts\python.exe main.py --universe fmp_listed --strategies proven_technology_emerging_tam
.venv-ui\Scripts\python.exe main.py --symbols AAPL,MSFT,GOOGL --strategies ttm_return_on_equity,return_on_assets,roe_improvement,return_on_capital_employed
.venv-ui\Scripts\python.exe main.py --workflow workflows/profitability_traits.json --output output/profitability
```

`--strategies all` runs the 15 default screens, excluding TAM and the four opt-in profitability screens. A comma-separated list runs screens independently; a workflow defines sequential routing. [Profitability formulas, default thresholds and parameters](../guides/profitability_traits.md). `return_on_equity` is the annual average-equity screen; `ttm_return_on_equity` is the distinct TTM closing-equity screen.

`screeners/utils.py` is a separate legacy function discovery path and is not the CLI/editor catalog.
