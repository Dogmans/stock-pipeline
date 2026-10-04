# Insider buying screen

Registered ID: `insider_buying`; class: `InsiderBuyingScreener(lookback_days=60)`. Initial pass condition is at least 65/100, configurable through the editor's ordinary score override or the existing threshold setting.

The score combines insider activity (up to 40), acceleration (25), price consolidation (20) and volume expansion (15). The result and stock sidebar retain component values and technical-data availability. These patterns do not predict a future price move.

Purchase classification requires acquisition, a purchase/buy transaction label and positive price; awards/grants are excluded from purchase signals. Sales use disposition plus a sale/sell label. Acceleration analysis has separate logic and should not be assumed to apply every purchase qualification identically.

Data comes from stable `insider-trading/search` per symbol, using a limited response filtered to the requested lookback. This is not a bulk paginated scan of every market transaction. Empty or sparse responses and limited historical price coverage affect interpretation.

```powershell
.venv-ui\Scripts\python.exe main.py --symbols AAPL,MSFT --strategies insider_buying
```

```python
from utils import run_screener
results = run_screener('insider_buying', universe_df, lookback_days=90)
```

[Provider routing](../provider_guides/financial_modeling_prep.md), [research views](../stock-research.md). Dated insider investigation results remain in the development archive; their timing and coverage figures are not current guarantees.
