# Researching a shortlist

Run a workflow, select an output node, then use the tabs in the results panel:

- **Stocks:** the original outcome table, CSV export and stock sidebar.
- **Rank:** each screener on the selected path becomes a separate factor. Adjust weights from 0 to 10. Values become percentiles within the selected outcome, using the applied rule's direction. Ties use midranks. All active factors must be present for an overall weighted rank; missing values are not treated as zero or silently excluded. A single-stock sample has percentile 50. These ranks describe the current sample, not expected returns.
- **Compare:** select two to five stocks and load aligned valuation, profitability, debt, cash flow and annual revenue growth. Quote and statement currencies and periods are displayed. Annual revenue growth requires consecutive annual periods and matching known currencies. Missing fields remain visible.
- **Near misses:** inspect failed evaluations within a configurable percentage of the threshold on the selected path. Clicking a symbol opens its actual failed route. Later screens may not have evaluated it. At a zero threshold, only exact-boundary failures have a defined relative distance. The 52-week-low default uses percentage above the low, rather than its inverted score.
- **Changes:** choose an earlier saved run to see entrants, departures and changed decisions for retained stocks. Both runs' recorded per-screen scores and explanations are shown. Changes may result from different rules, universes or data; they are not automatically attributed to market movements.
- **Saved runs:** reopen the exact workflow and results of a completed run. Snapshots are stored locally in `output/workflow_history`, independently of the short-lived score cache. Restoring a run does not fetch prices or rerun its screens. The next execution starts a new score snapshot.
- **Performance:** for an output containing at most 100 stocks, compare subsequent equal-weight price returns against a user-selected benchmark (SPY by default). Entry is the first benchmark close strictly after the saved run's date. Every stock must have prices on the same entry and end dates before a portfolio result is shown. At least two subsequent benchmark closes are needed. This is forward tracking, not a historical strategy backtest. Raw closing prices exclude dividends and trading costs and may be affected by corporate actions; the existing provider retrieves up to five years of prices.

The stock sidebar adds sector percentiles among the stocks evaluated at each screening step. This is a sample comparison, not an industry-wide ranking. At least two stocks with a known matching sector and numeric metric are required. The financial-history button loads up to five annual reporting periods, with revenue, earnings, margin, debt and free cash flow where available.

Selecting a screener shows its numeric distribution and applied threshold. Its canvas dropdown displays the compact rule. The sidebar shows source, reporting periods, quote timestamp, retrieval timestamp and missing-field coverage where the provider supplies them. Existing cache entries may lack newly added metadata; they remain labelled unavailable until refreshed through the normal cache lifecycle. Starting a new score snapshot does not bypass the underlying FMP data cache.

The universe selector supports the existing S&P 500, Nasdaq 100 and Russell 2000 sources. Optional exchange, minimum market-cap and average daily share-volume filters run before screening. Exchange matches the provider's full or short exchange name. Market-cap minimums are in the quote currency. Excluded and unavailable candidates remain inspectable in the source node's outcome tabs. Filtering needs company data for every candidate, so a broad universe can take longer.

## Return on equity

The `return_on_equity` screener calculates **annual net income / average opening and closing shareholders’ equity × 100**. Its score and editable `min_roe` parameter are percentage points (15 means 15%). The initial minimum is 15%; this is a configurable research threshold, not a universal quality benchmark.

It requires matching annual statement dates, matching known currencies, positive opening and closing shareholders’ equity, and positive asset balances. Its editable `min_equity_ratio` defaults to 5% average equity / average assets. Thin or nonpositive equity bases are marked unavailable, with reasons retained; a score override cannot bypass unavailable data. The annual measure is deliberately distinct from the provider's overview field labelled TTM.

Open **ROE history and equity checks** in the results or stock sidebar for annual values, equity-base checks and a three-year average when three consecutive valid years exist. Five annual balance sheets typically support four annual ROE calculations. Sector comparisons and percentile ranking work through the existing research views. Quality and Enhanced Quality already use ROE, so giving all three ranking weight increases its influence.

## Price change

The `price_change` node checks an inclusive minimum/maximum percentage change (defaults: 0% to 100%). Choose 1 week, 1/3/6 months or 1 year, approximated as 5/21/63/126/252 trading sessions, or 1-1260 custom sessions. Negative bounds can screen for declines.

The calculation is `(end close / start close - 1) * 100`, using FMP stable daily split-adjusted closes, excluding dividends and today's potentially incomplete bar. Each result records the actual endpoint dates and prices in its calculation details. A period needs N+1 observations; insufficient history, invalid prices, duplicate dates or gaps exceeding 10 calendar days produce Unavailable. Periods count observed sessions, not exact calendar months; smaller missing-data gaps cannot be distinguished from exchange closures.

Near misses check both range boundaries; distributions show both limits. Higher returns receive higher percentile ranks, which measures price strength rather than valuation.

## Validation

```powershell
cd web
npm test
npm run build
npx playwright test
```

Playwright uses Chromium by default. Set `STOCK_UI_BROWSER_CHANNEL=msedge` to use installed Edge. `STOCK_UI_EXTERNAL_SERVER=1` and `STOCK_UI_BASE_URL` allow testing an already-served production build. Browser tests stub API data; they do not use paid market-data requests.

```powershell
.venv-ui/Scripts/python.exe -m unittest tests.test_research tests.test_workflow tests.test_visual_api tests.test_fmp_transport
```
