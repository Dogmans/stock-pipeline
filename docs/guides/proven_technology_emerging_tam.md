# Proven Technology / Emerging TAM candidate screen

`proven_technology_emerging_tam` is one configurable flow box that creates a broad
quantitative research universe. It does not verify technology or TAM and applies
no thematic keywords, positive sector restrictions, profitability requirement,
or minimum priority score.

Add the box from the editor library. Select it to edit parameters, using the same
controls as the other screens. Empty inputs use the constructor defaults; zero
is an explicit value. The run records every effective setting, so changing the
workflow later cannot rewrite the recorded checks.

## Default eligibility checks

| Check | Default |
|---|---|
| Market cap | USD 100m–2.5bn, inclusive |
| Revenue | Greater than USD 20m |
| Gross margin | Greater than 20% |
| Revenue growth | Greater than −15% |
| Estimated average daily traded value | At least USD 100,000 |
| Financial survivability | Positive operating cash flow OR at least 12 months of cash runway |
| Latest required statement age | At most 550 days; future dates rejected |
| Exchanges | NASDAQ, NYSE, AMEX, TSX, TSXV |
| Domicile countries | Unrestricted; optional comma-separated country codes |
| Security eligibility | Active operating companies; exclude ETFs, funds, financials, REITs, shells and classified exploration businesses |

Missing required data produces an Unavailable outcome. A known failure remains
a failure even when other data is missing. Classification uses FMP flags and
industry/sector categories; ambiguous classifications require qualitative review.
Biotechnology companies with operating revenue can pass. Exploration-and-production
operating companies are not automatically excluded.

## Metrics and priority

Revenue, gross margin and growth use eight consecutive same-currency quarters
for current and previous TTM periods. If unavailable, use two consecutive annual
statements. Four available quarters can still supply current TTM metrics, with
growth unavailable. Cash flow uses four consecutive quarters or one annual
statement; the balance sheet uses the latest quarterly or annual observation.
All bases and dates are exported, along with the financial-statement rows.

Current quote FX converts market cap, revenue and trading value to USD; this is
a current research snapshot, not a historical backtest. Traded value is price
times FMP average share volume, not a measured average of daily dollar turnover.
Cash runway is cash plus liquid short-term investments divided by negative
operating cash flow, times 12 months. Restricted cash and debt maturity schedules
are not reliably resolved by this proxy; verify them during research.

Priority starts at 100. Configurable penalty thresholds default to EV/sales 8×,
debt/EBITDA 4× and annual dilution 10%. Each excess deducts
`min(maximum_points, max(0, actual - threshold) / max(abs(threshold), 1) * maximum_points)`.
Maximum deductions are 20, 20 and 15 respectively. Missing penalty metrics deduct
5 points each. Debt with nonpositive EBITDA deducts an additional 15 points;
current ratio below 1 deducts 5. These are priority penalties, never eligibility
exclusions. Share-count dilution is a proxy that can reflect stock splits or
corporate actions; verify large changes in research.

EV/sales uses an explicit proxy: market cap plus total debt minus cash and
short-term investments, converted to USD, divided by revenue. Minority interests
and preferred equity are not included. Debt/EBITDA and runway require matching
statement currencies. Negative or missing denominators are not coerced to zero.

## Universe and performance

The new `fmp_listed` universe uses FMP's paginated stable company screener by exchange and selects the five
default exchanges above. It preserves dotted ticker suffixes and does not use
ETF holdings or index constituents. Its coverage is provider coverage, not a
guarantee of every exchange listing. Missing exchange metadata fails explicitly.
The editor supports up to 25,000 records for this named universe.

Changing the screener's exchange setting does not expand its input universe;
use a custom symbol list for other exchanges. Existing universes remain unchanged.
Listings are unique by ticker, not by issuer: ADRs and multiple share classes
can require consolidation in subsequent research.

Profile metadata is fetched first. Structural exclusions and companies outside
the configurable market-cap enrichment buffer (default 50% beyond each boundary)
skip financial calls. Their audit records show Not evaluated for skipped checks.
This buffer does not relax eligibility. Fully enriched records normally need a
profile and three statement calls, with additional annual fallbacks and shared
FX calls as necessary. Requests share the existing 300/minute limiter; transient
429/server failures receive bounded retries and are not cached as empty results.
Successful responses are cached for 24 hours. Account entitlements still apply.

## Results

Pass and Fail branches remain eligibility outcomes, independent of priority or
export limits. Export up to 250 candidates and 100 near misses from the inspector.
All surplus survivors and all failures remain in the complete audit. Near misses
exclude known structural exclusions and sort by failed/unknown/skipped check count,
normalized threshold distance, priority, then ticker. No thresholds are silently
relaxed to fill either list.

The summary records a sequential funnel, effective settings and separate
`HIMX`, `LTRX`, `PNG.V` diagnostics. Benchmarks missing from the input are evaluated
without adding them to universe or survivor counts. No benchmark receives an
exemption.

CLI defaults:

```powershell
python main.py --universe fmp_listed --strategies proven_technology_emerging_tam
```

For customized settings, save a workflow from the editor and run:

```powershell
python main.py --workflow workflows/proven_technology_emerging_tam.json
```

Both paths write summary, candidates, near misses and audit JSON. Workflow runs
also retain this information in per-node results and history. The new screen is
opt-in and excluded from legacy `--strategies all` and default combined screens.

## Using the review queue in the editor

The box is available in the screen library. Its inspector records the effective
settings used for a completed run and offers dedicated exports. The generic
Near misses tab measures distance to a single numeric threshold; use TAM's
dedicated near-miss export for this multi-rule screen. Upstream boxes or source
filters can remove companies before this node evaluates them; the funnel describes
the node's input, not a reconstructed complete exchange universe.

The supplied example has output collections for all survivors, failures and
unavailable data. Consequently the workflow-wide combined shortlist includes
records from all three collections. Use the survivors collection or TAM's
candidate export when sending eligible companies to subsequent research.

Live check on 2026-10-04: the configured account permits NASDAQ, NYSE and AMEX listing queries, but returns HTTP 402 for TSX and TSXV. The default full discovery run therefore stops rather than silently dropping Canadian coverage. Account permissions can change.
