# Data Provider Architecture

This guide explains the data provider architecture used in the stock pipeline project.

## Overview

Our system uses specific providers for each data type:
- **Financial Modeling Prep**: Primary provider for stock data and fundamentals
- **YFinance**: Used for market indexes and VIX data

## Provider Structure

| File | Description |
|------|-----------|
| `data_providers/base.py` | Abstract base class defining the provider interface |
| `data_providers/yfinance_provider.py` | Yahoo Finance implementation |
| `data_providers/financial_modeling_prep.py` | Financial Modeling Prep implementation |

## Usage Examples

```python
# Use the default provider (Financial Modeling Prep)
import data_providers
provider = data_providers.get_provider()
data = provider.get_historical_prices(['AAPL', 'MSFT'], period='1y')

# Explicitly use a specific provider
from data_providers.yfinance_provider import YFinanceProvider
yf_provider = YFinanceProvider()
market_data = yf_provider.get_historical_prices(['^GSPC', '^VIX'], period='1m')
```
