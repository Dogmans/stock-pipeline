# Provider guides

The supported provider factory has FMP and YFinance. Registered screens use FMP directly; choosing an alternate CLI provider does not replace their data access. [Provider architecture](../data_providers/README.md).

- [FMP implementation and endpoint routing](provider_guides/financial_modeling_prep.md).
- [Normalized FMP field reference](provider_guides/fmp_field_reference.md).
- [Cache and refresh semantics](cache_usage.md).
- [TAM discovery data and calculations](guides/proven_technology_emerging_tam.md).
- [Dated performance investigation](fmp_performance.md).

```python
from data_providers import get_provider
provider = get_provider('financial_modeling_prep')
income = provider.get_income_statement('AAPL', annual=True)
if not income.empty:
    print(income[['fiscalDateEnding', 'totalRevenue']])
```

Do not assume a field exists because it is listed in a TypedDict. Check missing/nonfinite values and denominator validity. Ratios expressed as decimals require multiplication by 100 for percentage-point display. Reporting currency, quote currency and metric period must remain visible when combining financial and market values.
