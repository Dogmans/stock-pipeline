"""
Multi-provider for retrieving financial data from multiple sources with fallbacks.

This module implements the BaseDataProvider interface by combining multiple providers
with automatic failover to ensure data availability.
"""
from typing import Dict, List, Union, Any
import pandas as pd
import logging

from .base import BaseDataProvider
from .yfinance_provider import YFinanceProvider
from .alpha_vantage import AlphaVantageProvider
from .financial_modeling_prep import FinancialModelingPrepProvider
from .finnhub_provider import FinnhubProvider
from utils.logger import setup_logging

# Set up logger for this module
logger = setup_logging()

class MultiProvider(BaseDataProvider):
    """
    Multi-provider for financial data with automatic failover.
      Implements the BaseDataProvider interface by trying multiple data providers
    in sequence until one succeeds.
    """
    
    def __init__(self):
        """Initialize the Multi provider with all available providers."""
        self.providers = []
        
        # YFinance provider is always available and has no API limits
        self.providers.append(YFinanceProvider())
        
        # Financial Modeling Prep provider if API key is available (prioritized)
        try:
            self.providers.append(FinancialModelingPrepProvider())
        except Exception as e:
            logger.warning(f"Error initializing Financial Modeling Prep provider: {e}")
            
        # Alpha Vantage provider if API key is available (lower priority)
        try:
            self.providers.append(AlphaVantageProvider())
        except Exception as e:
            logger.warning(f"Error initializing Alpha Vantage provider: {e}")
        
        # Finnhub provider if API key is available
        try:
            self.providers.append(FinnhubProvider())
        except Exception as e:
            logger.warning(f"Error initializing Finnhub provider: {e}")
    
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data from multiple providers.
        
        Uses YFinance as primary provider for price data since it's the most reliable for this.
        
        Args:
            symbols: Single symbol or list of stock symbols
            period: Time period to retrieve (e.g., '1y', '6m', '1d')
            interval: Data interval (e.g., '1d', '1h', '5m')
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary mapping each symbol to its historical price DataFrame
        """
        # For price data, yfinance is the most reliable and has no limits
        # So we'll use it as the primary source
        if isinstance(self.providers[0], YFinanceProvider):
            try:
                result = self.providers[0].get_historical_prices(symbols, period, interval, force_refresh)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"YFinance provider failed for prices: {e}")
        
        # Try other providers if yfinance fails
        for provider in self.providers[1:]:
            try:
                result = provider.get_historical_prices(symbols, period, interval, force_refresh)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"{provider.get_provider_name()} failed for prices: {e}")
        
        # If all providers fail, return empty dict
        logger.error(f"All providers failed to get historical prices for {symbols}")
        return {}
    
    def get_income_statement(self, symbol: str, 
                            annual: bool = True,
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        Get income statement data from multiple providers.
        
        Tries providers in sequence until one succeeds.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing income statement data
        """
        # Try providers in sequence
        for provider in self.providers:
            try:
                result = provider.get_income_statement(symbol, annual, force_refresh)
                if not result.empty:
                    return result
            except Exception as e:
                logger.warning(f"{provider.get_provider_name()} failed for income statement: {e}")
        
        # If all providers fail, return empty DataFrame
        logger.error(f"All providers failed to get income statement for {symbol}")
        return pd.DataFrame()
    
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data from multiple providers.
        
        Tries providers in sequence until one succeeds.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing balance sheet data
        """
        # Try providers in sequence
        for provider in self.providers:
            try:
                result = provider.get_balance_sheet(symbol, annual, force_refresh)
                if not result.empty:
                    return result
            except Exception as e:
                logger.warning(f"{provider.get_provider_name()} failed for balance sheet: {e}")
        
        # If all providers fail, return empty DataFrame
        logger.error(f"All providers failed to get balance sheet for {symbol}")
        return pd.DataFrame()
    
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data from multiple providers.
        
        Tries providers in sequence until one succeeds.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing cash flow data
        """
        # Try providers in sequence
        for provider in self.providers:
            try:
                result = provider.get_cash_flow(symbol, annual, force_refresh)
                if not result.empty:
                    return result
            except Exception as e:
                logger.warning(f"{provider.get_provider_name()} failed for cash flow: {e}")
          # If all providers fail, return empty DataFrame
        logger.error(f"All providers failed to get cash flow for {symbol}")
        return pd.DataFrame()
    
    def get_company_overview(self, symbol: str,
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data from multiple providers.
        
        Tries providers in sequence until one succeeds.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company overview data
        """
        # Try providers in sequence
        for provider in self.providers:
            try:
                result = provider.get_company_overview(symbol, force_refresh)
                if result and 'Symbol' in result:
                    # Add information about which provider was used
                    provider_name = provider.get_provider_name()
                    result['_provider_used'] = provider_name
                    logger.info(f"Using {provider_name} data for company overview of {symbol}")
                    return result
            except Exception as e:
                logger.warning(f"{provider.get_provider_name()} failed for company overview: {e}")
        
        # If all providers fail, return empty dict
        logger.error(f"All providers failed to get company overview for {symbol}")
        return {}
    
    def get_fundamental_data(self, symbol: str, 
                           force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive fundamental data for the specified symbol.
        
        This implementation optimizes by potentially using different providers
        for different parts of the data based on availability and API limits.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary with keys: 'income_statement', 'balance_sheet', 
                                'cash_flow', and 'overview'
        """
        result = {}
        
        # Get income statement
        result['income_statement'] = self.get_income_statement(symbol, force_refresh=force_refresh)
        
        # Get balance sheet
        result['balance_sheet'] = self.get_balance_sheet(symbol, force_refresh=force_refresh)
        
        # Get cash flow
        result['cash_flow'] = self.get_cash_flow(symbol, force_refresh=force_refresh)
        
        # Get overview
        result['overview'] = self.get_company_overview(symbol, force_refresh=force_refresh)
        
        return result
    
    def get_provider_name(self) -> str:
        """
        Get the name of this data provider.
        
        Returns:
            String name of the provider
        """
        return "MultiProvider"
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this data provider.
        
        Returns:
            Dictionary with provider information including all sub-providers
        """
        info = super().get_provider_info()
        info['sub_providers'] = [p.get_provider_info() for p in self.providers]
        return info
