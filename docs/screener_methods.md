# Registered screener reference

Profitability additions reviewed against the registry and catalog on 2026-10-27. These are the IDs accepted by the CLI and visual editor; there are 20 registered screens, 15 in the default `all` selection. The four TTM profitability screens and TAM are opt-in.

| Strategy ID | Initial pass rule | Editable constructor parameters |
| --- | --- | --- |
| `pe_ratio` | P/E <= 10 | `max_pe` |
| `peg_ratio` | PEG ratio <= 1.0 | `max_peg_ratio`, `min_growth` |
| `price_to_book` | Price / book <= 1.2 | `max_pb_ratio` |
| `sharpe_ratio` | Sharpe ratio >= 1.0 | `min_sharpe_ratio`, `lookback_period` |
| `price_change` | Price change 0.0 to 100.0% inclusive | `period`, `custom_days`, `min_change`, `max_change` |
| `momentum` | Momentum score >= 15.0% | `min_momentum_score`, `lookback_period` |
| `quality` | Quality score >= 6.0 | `min_quality_score` |
| `return_on_equity` | Annual ROE >= 15.0% | `min_roe`, `min_equity_ratio` |
| `ttm_return_on_equity` (opt-in) | TTM ROE >= 15.0% | `min_percent` |
| `return_on_assets` (opt-in) | TTM ROA >= 10.0% | `min_percent` |
| `roe_improvement` (opt-in) | ROE change over three years > 0.0pp | `min_percent` |
| `return_on_capital_employed` (opt-in) | TTM ROCE >= 30.0% | `min_percent` |
| `fcf_yield` | Free cash flow yield >= 3.5% | `min_fcf_yield` |
| `enhanced_quality` | Quality score >= 50.0 / 100 | None |
| `insider_buying` | Insider buying score >= 65.0 / 100 | `lookback_days` |
| `fifty_two_week_lows` | Price above 52-week low <= 15% | None |
| `historic_value` | Historic value score >= 25.0 | `min_historic_value_score`, `lookback_period` |
| `analyst_sentiment_momentum` | Sentiment score >= 1.0 / 100 | `lookback_days` |
| `composite_score` | Composite score >= 60.0 / 100 | None |
| `proven_technology_emerging_tam` | All hard checks; priority score does not determine pass | `min_market_cap`, `max_market_cap`, `min_revenue`, `min_gross_margin_pct`, `min_revenue_growth_pct`, `min_daily_dollar_volume`, `min_runway_months`, `max_ev_sales`, `max_debt_ebitda`, `max_dilution_pct`, `max_statement_age_days`, `candidate_limit`, `near_miss_limit`, `enrichment_buffer_pct`, `exchanges`, `countries` |

## Behaviour and units

Defaults can come from constructors or `config.ScreeningThresholds`. Some older constructors use `value or default`, so zero falls back to the configured default; the catalog records this where applicable. TAM and the four TTM profitability screens treat zero as an explicit value. Score thresholds, ratios and percentage points are not interchangeable.

`quality` uses a 10-point score and needs at least three overview metrics. Its strict component boundaries include ROE above 15%, debt/equity below 0.5, profit margin above 20%, operating margin above 15% and EV/EBITDA below 10. `enhanced_quality` allocates up to 25 points each to ROE, profitability, financial strength and growth quality, passing at 50; configuration component constants are not independent flow checks.

`return_on_equity` uses annual income and average positive equity. The four new profitability screens use four reported quarters and closing balance-sheet denominators: ROE = net income / shareholders' equity; ROA = net income / assets; ROCE = EBIT / (assets minus current liabilities). `roe_improvement` measures the change in TTM ROE from the same fiscal quarter three years earlier. Equality fails its default strict `>` rule. Its score and `min_percent` are percentage points; the other three scores and thresholds are percentages. Missing data remains unavailable.

These four screens share calculations with the stock pages, rank higher scores first and apply no sector exclusions individually. The supplied [profitability workflow](../workflows/profitability_traits.json) stacks them with the video's sector exclusions. Provider overview names ending in `TTM` can contain annual ratios and are separate from these calculated values. [Formulas, units and coverage](guides/profitability_traits.md).

`price_change` uses split-adjusted closes and an inclusive range. [Research methodology](stock-research.md).

`analyst_sentiment_momentum` has a default score threshold of 1 for exploratory use; sparse analyst coverage remains a limitation. `composite_score` weights available factors, requires at least three and passes at 60. It is independent of the legacy average-rank combined helpers.

`proven_technology_emerging_tam` is opt-in. It has no positive theme/sector filter and retains rule evidence, unknowns and scoring penalties. [Complete TAM policy and exports](guides/proven_technology_emerging_tam.md).

## Legacy modules

Turnaround, fallen IPO, sector correction and combined-function modules still exist but are not registered CLI strategy IDs or editor boxes. Import them directly when needed. Historical names such as `value`, `growth`, `52_week_lows` and `combined` are not accepted aliases in the current registry.

[Strategy names](screener_methods/strategy_names.md), [package structure](screener_methods/package_structure.md), [result behaviour](screener_methods/enhanced_behavior.md), [legacy combined semantics](screener_methods/combined.md).
