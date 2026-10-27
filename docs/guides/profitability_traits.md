# Four profitability traits

Source: [Investor52: 4 Traits That Find Better Stocks (And Who Fits Now?)](https://www.youtube.com/watch?v=ESjh3718bnI). The four primary filters appear at approximately 1:44, 5:44, 6:50 and 8:58. These are configurable research filters; the video's historical return claims are not reproduced or backtested here.

| Screen / CLI ID | Default | Calculation |
| --- | --- | --- |
| `ttm_return_on_equity` | ROE >= 15% | Sum of net income for four consecutive fiscal quarters / closing shareholders' equity |
| `return_on_assets` | ROA >= 10% | The same TTM net income / closing total assets |
| `roe_improvement` | Change > 0 percentage points | Current TTM ROE minus TTM ROE at the same fiscal quarter three years earlier |
| `return_on_capital_employed` | ROCE >= 30% | TTM EBIT / (closing total assets minus current liabilities) |

EBIT uses the reported `ebit` field, or net income + income tax expense + interest expense when all three components exist. Operating income is not silently substituted. Ratios are fractions in the stock API and profitability CSV; screen scores are percentages or percentage points. A 20% ROE has API value 0.2 and screener score 20. A rise from 10% to 20% is +10pp, not 100% growth.

The existing `return_on_equity` screen retains its annual net income / average opening and closing equity definition and its minimum equity/assets check. Its scores can differ from the new TTM closing-equity metric. Provider annual ROE in the screening snapshot is labelled separately.

## Stock pages and screening

- Overview, Financials and the screening stock dialog share the profitability panel, historical charts and CSV export.
- The screening Compare tab includes the four metrics, the older ROE value and both reporting dates.
- All four screens appear in the library and support independent `min_percent` settings. Improvement uses a strict greater-than rule; equality fails. Custom generic score overrides use their explicitly selected inclusive comparison.
- Select **Load four profitability traits** in the library, or open `workflows/profitability_traits.json`, to stack all four screens in the video's order. Loading the preset replaces the current canvas; save an existing workflow first if needed.
- The preset starts from the S&P 500 and excludes Financial Services / Financials, Energy, Utilities, Basic Materials / Materials, and Real Estate. Excluded sectors are editable under Universe eligibility filters. Standalone profitability screens apply no sector exclusion. Unknown sector classifications remain unavailable when exclusions are enabled.
- These four screens are opt-in for CLI `--strategies all`; they are available by their explicit IDs or through the preset workflow. The 15 existing defaults are unchanged.

## Coverage and alignment

The provider supplies up to forty quarterly income and balance-sheet observations through the existing research statement cache. Each TTM observation requires four distinct, consecutive fiscal quarters, correctly ordered Q1-Q4 with gaps of 65-115 days, and a balance sheet at exactly the income period's date. All five statement currencies must be known and agree. The three-year comparison matches the same fiscal quarter 1060-1130 days earlier and the same reported currency; typically sixteen quarters of history are needed. Changes in fiscal calendars or missing quarter labels can leave values unavailable.

Nonpositive equity, assets or capital employed make the corresponding ratio unavailable. Zero or negative profits remain valid observations when the denominator is positive. Missing inputs do not become zero. The latest period never falls back to an older valid value. A missing three-year comparison does not hide current ROE, ROA or ROCE. Provider exceptions go to the workflow Error branch; a successful empty response or insufficient financial history goes to Unavailable. Company pages retain their other data when profitability statements fail.

Statement dates and calculation inputs accompany each screening result. Availability depends on FMP coverage and subscription access, especially the sixteen-quarter history needed for the ROE trend. Data can be cached; this feature does not change provider expiry windows.
