"""
Data providers package for the stock pipeline.

This package contains modules for retrieving financial data from various sources.
Each module implements the BaseDataProvider interface to ensure consistent behavior.

Type Definitions:
    For FMP API response structures, see fmp_types.py:
    - FMPCompanyOverview: Company overview/profile data
    - FMPIncomeStatement: Income statement rows
    - FMPBalanceSheet: Balance sheet rows  
    - FMPCashFlow: Cash flow rows
    - FMPHistoricalPrice: Price history rows
    
    Import example:
        from data_providers.fmp_types import FMPCompanyOverview
        overview: FMPCompanyOverview = provider.get_company_overview('AAPL')
"""

from .base import BaseDataProvider
from .yfinance_provider import YFinanceProvider
from .financial_modeling_prep import FinancialModelingPrepProvider

# Type definitions for FMP API
from .fmp_types import (
    FMPCompanyOverview,
    FMPIncomeStatement,
    FMPBalanceSheet,
    FMPCashFlow,
    FMPHistoricalPrice,
    FMPPriceTarget,
    FMPAnalystGrades
)

# Default provider instance for easy access - Financial Modeling Prep
default_provider = FinancialModelingPrepProvider()

# Factory function to create a provider instance by name
def get_provider(provider_name=None):
    """
    Get a provider instance by name.
    
    Args:
        provider_name (str): Name of the provider. If None, returns the default provider.
        
    Returns:
        BaseDataProvider: Provider instance.
    """
    providers = {
        'yfinance': YFinanceProvider(),
        'financial_modeling_prep': FinancialModelingPrepProvider(),
    }    
    if provider_name is None:
        return default_provider
    
    provider = providers.get(provider_name.lower())
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider
