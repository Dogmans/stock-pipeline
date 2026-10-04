# Using data providers

```python
from data_providers import get_provider
provider = get_provider('financial_modeling_prep')
overview = provider.get_company_overview('AAPL')
prices = provider.get_historical_prices('AAPL', period='1y')
```

Only FMP and YFinance are supported factory names. Registered screens normally construct their own FMP provider; CLI provider selection does not replace it. Discovery uses a separate `FMPScreeningProvider` for stable requests and FX.

See [provider architecture](../../data_providers/README.md), [FMP implementation](../provider_guides/financial_modeling_prep.md), [field reference](../provider_guides/fmp_field_reference.md) and [cache semantics](../cache_usage.md).
