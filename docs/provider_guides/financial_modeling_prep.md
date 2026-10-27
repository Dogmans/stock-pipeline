# FMP implementation guide

This page describes repository behaviour, not a guarantee of current subscription coverage. The implementation is [financial_modeling_prep.py](../../data_providers/financial_modeling_prep.py); discovery access is [fmp_screening.py](../../data_providers/fmp_screening.py).

## Existing provider

`_make_api_request()` returns `(success, data, error)` and routes ordinary endpoints to `/api/v3/{endpoint}/{symbol}`. Its selected stable endpoints use query-string symbols. It shares a module-level Requests session and calls the shared request limiter before requests. Central requests have 5-second connect and 20-second read timeouts; other methods have their own paths. There is no universal retry policy in this existing helper.

| Method | Data/API behaviour | Cache |
| --- | --- | --- |
| `get_company_overview` | Profile + quote + annual key metrics; ratios when valuation fields are missing; market-cap endpoint if needed | 24h, versioned key |
| `get_income_statement` | Legacy income statement, five annual rows or configured quarterly count (default six) | 168h |
| `get_balance_sheet` | Legacy balance-sheet statement, same limits | 168h |
| `get_cash_flow` | Legacy cash-flow statement, same limits | 168h |
| `get_research_statements` | Raw stable income/balance/cash-flow statements; up to ten annual periods or forty quarters | 24h |
| `get_historical_prices` | Legacy price history; returns a symbol-to-DataFrame mapping | 24h |
| `get_price_change_history` | Stable `historical-price-eod/full`, shared symbol/date coverage, split-adjusted closes | Incremental tail refresh; weekly reconciliation |
| `get_stock_news` | Stable `news/stock` | 30min |
| `get_insider_trading` | Stable `insider-trading/search` for a symbol, limited response filtered by lookback | 24h |
| Analyst/price-target methods | Selected stable grades, estimates and targets | No blanket cache guarantee; inspect individual methods |

Legacy normalized statements rename `date` to `fiscalDateEnding`, convert it to datetime, sort newest first and retain unrenamed source fields. [Field mapping reference](fmp_field_reference.md).

Overview profitability fields are conditional on the ratios request; names labelled TTM do not establish a TTM period because the request uses annual ratios. `RevenueGrowth` is declared in the type but not populated by the existing overview. `DataCompleteness` is a coarse fetch-stage label, not validation of every metric.

## Calculated profitability

`profitability.py` requests raw quarterly income and balance-sheet data through `get_research_statements()`. It supplies the stock-detail API and the four profitability screeners, with closing-balance TTM ROE, ROA and ROCE plus a same-quarter three-year ROE comparison. Raw research frames retain source field names and dates; the adapter aligns and sorts observations itself. It accepts shareholder-equity aliases, requires known matching currencies, and leaves incomplete or unsuitable ratios unavailable.

The accessor raises when the request fails or the payload is not a list; a successful empty list remains an empty DataFrame. The stock service catches statement-fetch exceptions to retain the rest of the company view. Profitability screens propagate them to the workflow Error branch; successful but insufficient history produces Unavailable. These requests retain the existing shared transport and limiter, without adding a retry policy or altering legacy statement limits. [Calculations, coverage and units](../guides/profitability_traits.md).

## Discovery provider

`FMPScreeningProvider` subclasses the existing provider but isolates stable requests through `fetch()`. It requests stable profile, company-screener, quote (FX), income, balance-sheet and cash-flow endpoints. Requests use the shared session/limiter and 5/20-second timeouts. Up to three attempts retry 429 and selected server errors, with waits capped at 30 seconds. Successful record lists are memoized for 24h; empty lists are accepted only for listing pagination. Failures raise without caching an empty result.

`statements()` requests eight quarterly rows or three annual rows, then normalizes selected fields. The TAM screener validates and selects the required periods. `usd_rate()` uses direct or inverse currency-pair quotes, and rejects missing conversion data. The listing universe uses paginated company-screener requests and requires exchange metadata and selects NASDAQ/NYSE/AMEX/TSX/TSXV without cap or volume prefilters. See [the TAM guide](../guides/proven_technology_emerging_tam.md) for formulas and limitations.

## Refresh and errors

Existing `force_refresh=True` methods can clear the global cache. Memoized argument forms matter: positional and keyword calls can have different cache keys. Discovery has no `force_refresh` argument; clear its exact memoization key or use normal expiry. The standalone CLI refresh flag clears the cache before a normal run; workflow CLI dispatch happens before that cache-management path.

Some existing methods convert API failures to empty data. Preserve unknown/unavailable states in consumers; do not replace absent revenue, equity, cash or ratios with zero. Existing universe requests do not all use the shared provider transport or limiter.

Live check on 2026-10-04: the configured account permits NASDAQ, NYSE and AMEX listing queries, but returns HTTP 402 for TSX and TSXV. The default full discovery run therefore stops rather than silently dropping Canadian coverage. Account permissions can change.
