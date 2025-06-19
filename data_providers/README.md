# Data Provider Architecture

This directory contains the data provider abstraction layer that allows the stock pipeline to retrieve financial data from multiple sources with automatic failback and error handling.

## Provider Priority (as of June 18, 2025)

Providers are tried in the following order in the MultiProvider:

1. **YFinance** - Always available with no API key required, but limited data for some metrics
2. **Financial Modeling Prep** - Primary API source, comprehensive data with good documentation (PREFERRED)
3. **Alpha Vantage** - Secondary API source, fallback when FMP is unavailable
4. **Finnhub** - Additional data source, mainly for real-time quotes and technical indicators

## API Limits

| Provider | Free Tier Limits | Premium Options |
|----------|------------------|-----------------|
| YFinance | No official limit, but rate limiting applies | N/A (Open source) |
| Financial Modeling Prep | 250-300 calls/day | Starting ~$14/month |
| Alpha Vantage | 5 calls/min, 500 calls/day | Starting ~$50/month |
| Finnhub | 60 calls/min | Starting ~$15/month |

## Best Practices

1. **Use Chunking**: For large universes like SP500, use the chunking functionality to stay within API limits:
   ```powershell
   python main.py --universe sp500 --chunk-size 50
   ```

2. **Leverage Caching**: Most API responses are cached for 24 hours (prices) or 1 week (fundamentals)

3. **Prefer Direct Provider Selection** for specific needs:
   ```powershell
   python main.py --data-provider financial_modeling_prep
   ```

4. **Use MultiProvider** for production:
   ```powershell
   python main.py --multi-source
   ```

## Implementation Details

Each provider implements the BaseDataProvider interface defined in `base.py`. This ensures consistent method signatures and behavior across all providers.

### Adding a New Provider

1. Create a new file: `my_provider.py`
2. Implement the BaseDataProvider interface
3. Add it to the provider registry in `__init__.py`
4. Update the MultiProvider to include it

### Provider Statistics

You can view statistics about data provider performance with:

```powershell
python main.py --provider-stats
```

This shows success rates, call counts, and errors for each provider.

## Testing Provider Priority

The provider priority order is enforced in the `MultiProvider` class and verified by unit tests:

```powershell
python -m unittest tests.test_provider_priority
```

The tests verify that:
1. Providers are initialized in the correct order
2. The fallback mechanism works properly
3. Results include provider tracking information

You can also check the current provider order with:

```powershell
python -c "import data_providers; provider = data_providers.get_provider('multi'); print([p.get_provider_name() for p in provider.providers])"
```
