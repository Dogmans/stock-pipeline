"""
Data providers package for the stock pipeline.

This package contains modules for retrieving financial data from various sources.
Each module implements the BaseDataProvider interface to ensure consistent behavior.
"""

from .base import BaseDataProvider
from .alpha_vantage import AlphaVantageProvider
from .yfinance_provider import YFinanceProvider
from .financial_modeling_prep import FinancialModelingPrepProvider
from .finnhub_provider import FinnhubProvider
from .multi_provider import MultiProvider

# Default provider instance for easy access
default_provider = MultiProvider()

# Factory function to create a provider instance by name
def get_provider(provider_name=None):
    """
    Get a provider instance by name.
    
    Args:
        provider_name (str): Name of the provider. If None, returns the default MultiProvider.
        
    Returns:
        BaseDataProvider: Provider instance.
    """
    providers = {
        'alpha_vantage': AlphaVantageProvider(),
        'yfinance': YFinanceProvider(),
        'financial_modeling_prep': FinancialModelingPrepProvider(),
        'finnhub': FinnhubProvider(),
        'multi': MultiProvider(),
    }
    
    if provider_name is None:
        return default_provider
    
    provider = providers.get(provider_name.lower())
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider
