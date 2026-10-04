# PEG ratio screen

Registered ID: `peg_ratio`; class: `PEGRatioScreener`. Constructor defaults are `max_peg_ratio=1.0`, `min_growth=5.0`.

The score is P/E divided by growth in percentage points: P/E 15 and growth 15% gives PEG 1. Growth first uses latest quarterly EPS versus four observations earlier, requiring positive current and prior EPS. Overview `EPSGrowth` or `RevenueGrowth` is a fallback when supplied; the existing FMP overview does not currently populate those fields.

Nonpositive P/E, absent/nonpositive growth or growth above 100% yields no valid score. Valid PEG passes when at most `max_peg_ratio`; lower scores rank first. The current implementation accepts and stores `min_growth` but does not apply it as a minimum-growth gate. Do not infer that a configured 5% minimum is enforced.

```python
from utils import run_screener
from universe import get_stock_universe
results = run_screener('peg_ratio', get_stock_universe('sp500'), max_peg_ratio=0.8)
```

```powershell
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies peg_ratio
```

The legacy wrapper is imported directly from `screeners.peg_ratio`, not the package root. Historical growth is a screening proxy, not an analyst forecast. [Field coverage](../provider_guides/fmp_field_reference.md), [result behaviour](enhanced_behavior.md).
