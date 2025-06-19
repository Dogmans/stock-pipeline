# Data Provider Architecture

This directory contains the data provider abstraction layer that allows the stock pipeline to retrieve financial data from various sources.

## Provider Selection (as of June 19, 2025)

The project now directly uses specific providers for different data needs:

1. **Financial Modeling Prep** - Primary provider for most data (PREFERRED, default due to paid subscription)
2. **YFinance** - Used specifically for market indexes and VIX data where it excels
3. **Alpha Vantage** - Available for specific data types if needed
4. **Finnhub** - Available for specific real-time quotes and technical indicators if needed

## API Limits

| Provider | Limits | Notes |
|----------|--------|-------|
| YFinance | No official limit, but rate limiting applies | N/A (Open source) |
| Financial Modeling Prep | 300 calls/min, No daily limit | **PAID TIER** in use |
| Alpha Vantage | 5 calls/min, 500 calls/day | Free tier |
| Finnhub | 60 calls/min | Free tier |

## Rate Limiting (as of June 19, 2025)

The pipeline now includes automatic rate limiting to prevent exceeding API limits:

1. **Per-Provider Configuration**: Each provider has specific rate limits configured in `config.py`
2. **Automatic Throttling**: The system automatically waits when approaching limits
3. **Minute and Daily Limits**: Both per-minute and per-day limits are enforced
4. **Command Line Options**:
   ```powershell
   # Custom rate limit
   python main.py --data-provider financial_modeling_prep --custom-rate-limit 150
   
   # Disable rate limiting (not recommended)
   python main.py --data-provider financial_modeling_prep --disable-rate-limiting
   ```

## Best Practices

1. **Use Chunking**: For large universes like SP500, use the chunking functionality to stay within API limits:
   ```powershell
   python main.py --universe sp500 --chunk-size 50
   ```

2. **Leverage Caching**: Most API responses are cached for 24 hours (prices) or 1 week (fundamentals)

3. **Choose Specific Provider** for special cases:
   ```powershell
   python main.py --data-provider yfinance
   ```
   (Financial Modeling Prep is the default provider with paid subscription)

## Implementation Details

Each provider implements the BaseDataProvider interface defined in `base.py`. This ensures consistent method signatures and behavior across all providers.

### Adding a New Provider

1. Create a new file: `my_provider.py`
2. Implement the BaseDataProvider interface
3. Add it to the provider registry in `__init__.py`
4. Import it and use it directly in the appropriate modules

### Provider Statistics

You can view statistics about data provider performance with:

```powershell
python main.py --provider-stats
```

This shows success rates, call counts, and errors for each provider.

## Testing Providers

Each provider is tested individually:

```powershell
python -m unittest tests.test_providers
```

The tests verify that:
1. Each provider correctly retrieves data
2. The data format is standardized
3. Error handling works as expected

You can check the default provider with:

```powershell
python -c "import data_providers; provider = data_providers.get_provider(); print(provider.get_provider_name())"
```
