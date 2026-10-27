# Data providers

The current factory in `__init__.py` supports `financial_modeling_prep` (default) and `yfinance`. Alpha Vantage and Finnhub are not implemented providers in this repository. `multi_provider.py` is separate supporting code, not the factory used by registered screens.

```python
import data_providers
provider = data_providers.get_provider('financial_modeling_prep')
print(provider.get_provider_name())
```

Registered screeners create their own FMP providers. The standalone CLI's `--data-provider` affects market-context collection, not those screener instances. `--provider-stats`, `--custom-rate-limit` and `--disable-rate-limiting` are parsed but currently have no implementation in `main()`; do not rely on them. `--chunk-size` is not a supported flag.

The configured FMP limit is 300 requests/minute and no daily cap. These settings are repository assumptions, not verification of account entitlements. Existing selected methods also use cache-aware method throttling. FMP shares a Requests session; the new discovery provider shares the same session and request limiter.

| Implementation | Usage |
| --- | --- |
| `financial_modeling_prep.py` | Existing overview, normalized statements, price histories and auxiliary data; mixed legacy/stable endpoints |
| `fmp_screening.py` | Stable profile, listing universe, FX and eight-quarter statements for TAM; isolated from existing consumers |
| `fmp_types.py` | Documentation/typing for normalized existing-provider fields; not a promise of field availability |
| `yfinance_provider.py` | Alternate market/price data support |
| `base.py` | Provider interface |

The stock profitability panel and four opt-in screens share `profitability.py`. They use `get_research_statements(symbol, statement, annual=False)` for up to forty raw quarterly income/balance observations from the stable endpoints, cached for 24 hours. This is separate from the legacy five-year/six-quarter normalized statement methods and TAM's eight-quarter accessor. ROE/ROA/ROCE and the three-year ROE change are derived locally with aligned periods and known matching currencies; no provider overview ratio is substituted. [Definitions and API fields](../docs/guides/profitability_traits.md).

Cache expiry is method-specific. Discovery successes expire after 24 hours and exceptions are not memoized. Existing income/balance/cash-flow calls expire after a week and may cache empty results on failure. Existing `force_refresh` paths can clear the whole cache. See [cache semantics](../docs/cache_usage.md).

Read [the FMP guide](../docs/provider_guides/financial_modeling_prep.md) and [field reference](../docs/provider_guides/fmp_field_reference.md) before consuming data. Use [the offline test runner](../docs/testing.md) for mocked validation; legacy provider tests can contact live services.
