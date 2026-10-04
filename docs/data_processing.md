# Data processing contracts

## Universe inputs

Screeners receive a DataFrame with a `symbol` column. Universe rows may also contain company names, exchange or sector data; do not assume those fields are complete.

- S&P 500: FMP constituents; retrieval failure yields unavailable/empty data, not a cached substitute index.
- Russell 2000: FMP constituents, then IWM holdings fallback; its alphabetic-ticker cleanup can omit dotted symbols.
- NASDAQ/NASDAQ100: existing FMP path, with Nasdaq-100 Wikipedia fallback. The `nasdaq` label does not guarantee a complete exchange list.
- Dow: FMP constituents, with a separate fallback in the existing implementation.
- `all`: deduplicated union of these index sets, not every listed company.
- `country:<key>`: configured ETF holdings, not a complete country listing. Use mapping keys such as `country:japan`, `country:uk` or `country:canada`; unknown named universes can fall back to S&P 500.
- `fmp_listed`: paginated stable FMP company-screener scoped to NASDAQ/NYSE/AMEX/TSX/TSXV; preserves ticker suffixes and raises on missing exchange metadata.

## Financial and price normalization

[The field reference](provider_guides/fmp_field_reference.md) distinguishes raw FMP fields from normalized provider output. Statements use `fiscalDateEnding`, newest first; revenue is `totalRevenue`, balance cash is `cash`, and operating cash flow is `operatingCashflow`. Check both cash-flow spellings when consuming older data.

Existing historical-price calls return a mapping from ticker to DataFrame with `Open`, `High`, `Low`, `Close`, `Volume` and a date index. Price-change history is a separate DataFrame with `Date` and `Close`; its stable endpoint has a different adjustment basis. Do not interchange these without inspecting the consumer.

Overview ratios are generally decimals; screen-specific displayed percentages may be percentage points. Current ratio requires balance-sheet assets/liabilities. Reporting and quote currencies must match or be converted when combining amounts.

## TAM evaluation

TAM keeps input symbols even when required data is missing. Its isolated accessor requests eight quarters without changing legacy six-quarter defaults. It validates dates, consecutive periods and currencies, calculates TTM or disclosed annual fallback metrics, and records raw rows, source dates and FX evidence. Hard-rule results, priority penalties and export selection are independent. [Full methodology](guides/proven_technology_emerging_tam.md).

## Other analysis

Analyst sentiment uses the provider's stable grades/estimates/target methods. Coverage can be sparse and the default pass threshold is deliberately low; do not treat missing component coverage as confirmed positive evidence.

`technical_indicators.py` uses pandas/NumPy and optional TA-Lib. TA-Lib is not installed by the pinned requirements; pandas fallbacks exist. When calling TA-Lib directly, supply float64 NumPy arrays. The indicator function lowercases input columns and adds calculated columns; avoid assuming it preserves an untouched provider frame.

Cache expiry is per method. See [cache semantics](cache_usage.md) for correct invalidation; creating a new score snapshot does not guarantee new market data.

Live check on 2026-10-04: the configured account permits NASDAQ, NYSE and AMEX listing queries, but returns HTTP 402 for TSX and TSXV. The default full discovery run therefore stops rather than silently dropping Canadian coverage. Account permissions can change.
