"""
Alpha Vantage data provider for retrieving financial data.

This module implements the BaseDataProvider interface for Alpha Vantage API.
"""
from typing import Dict, List, Union, Any
import pandas as pd
import requests
import os
import logging

from .base import BaseDataProvider
from cache_manager import cache_api_call

import config
from utils import setup_logging

# Set up logger for this module
logger = setup_logging()

class AlphaVantageProvider(BaseDataProvider):
    """
    Alpha Vantage data provider for financial data.
    
    Implements the BaseDataProvider interface using Alpha Vantage API.
    """
    
    # API limits
    RATE_LIMIT = 5  # 5 calls per minute on free tier
    DAILY_LIMIT = 500  # 500 calls per day on free tier
    
    def __init__(self, api_key=None):
        """
        Initialize the Alpha Vantage provider.
        
        Args:
            api_key (str, optional): Alpha Vantage API key. If not provided,
                                    uses the key from config.
        """
        self.api_key = api_key or config.ALPHA_VANTAGE_API_KEY
        if not self.api_key:
            logger.warning("Alpha Vantage API key not provided")
        
        # Base URL for Alpha Vantage API
        self.base_url = "https://www.alphavantage.co/query"
    
    @cache_api_call(expiry_hours=24, cache_key_prefix="av_prices")
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data using Alpha Vantage API.
        
        Note: Alpha Vantage isn't ideal for bulk price data requests.
        Consider using YFinanceProvider for historical prices.
        
        Args:
            symbols: Single symbol or list of stock symbols
            period: Time period to retrieve (e.g., '1y', '6m', '1d')
            interval: Data interval (e.g., '1d', '1h', '5m')
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary mapping each symbol to its historical price DataFrame
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        result = {}
        
        # Map period to Alpha Vantage outputsize param
        outputsize = "full" if period in ("1y", "2y", "5y", "max") else "compact"
        
        # Map interval to Alpha Vantage function and interval params
        if interval in ("1d", "daily"):
            function = "TIME_SERIES_DAILY"
            av_interval = None
        elif interval in ("1wk", "weekly"):
            function = "TIME_SERIES_WEEKLY"
            av_interval = None
        elif interval in ("1mo", "monthly"):
            function = "TIME_SERIES_MONTHLY"
            av_interval = None
        else:
            function = "TIME_SERIES_INTRADAY"
            av_interval = interval
        
        for symbol in symbols:
            try:
                params = {
                    "function": function,
                    "symbol": symbol,
                    "outputsize": outputsize,
                    "apikey": self.api_key
                }
                
                if av_interval:
                    params["interval"] = av_interval
                
                response = requests.get(self.base_url, params=params)
                data = response.json()
                
                # Extract time series data
                if function == "TIME_SERIES_DAILY":
                    time_series_key = "Time Series (Daily)"
                elif function == "TIME_SERIES_WEEKLY":
                    time_series_key = "Weekly Time Series"
                elif function == "TIME_SERIES_MONTHLY":
                    time_series_key = "Monthly Time Series"
                else:
                    time_series_key = f"Time Series ({av_interval})"
                
                if time_series_key in data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data[time_series_key]).T
                    df.columns = [col.split(". ")[1] for col in df.columns]
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    df.index = pd.DatetimeIndex(df.index)
                    df = df.astype(float)
                    
                    # Limit to requested period
                    if period == "1m":
                        df = df.iloc[-30:]
                    elif period == "3m":
                        df = df.iloc[-90:]
                    elif period == "6m":
                        df = df.iloc[-180:]
                    elif period == "1y":
                        df = df.iloc[-365:]
                    
                    result[symbol] = df
                else:
                    logger.error(f"Error getting price data for {symbol}: {data.get('Error Message', 'Unknown error')}")
            
            except Exception as e:
                logger.error(f"Error getting price data for {symbol}: {e}")
        
        return result
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="av_income")  # Cache for 1 week
    def get_income_statement(self, symbol: str, 
                            annual: bool = True,
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        Get income statement data from Alpha Vantage API.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing income statement data
        """
        try:
            params = {
                "function": "INCOME_STATEMENT",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "annualReports" in data and "quarterlyReports" in data:
                reports = data["annualReports"] if annual else data["quarterlyReports"]
                df = pd.DataFrame(reports)
                
                # Convert date columns
                if "fiscalDateEnding" in df.columns:
                    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                    df = df.sort_values("fiscalDateEnding", ascending=False)
                
                return df
            else:
                error_msg = data.get("Error Message", "Unknown error")
                logger.error(f"Error getting income statement for {symbol}: {error_msg}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting income statement for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="av_balance")  # Cache for 1 week
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data from Alpha Vantage API.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing balance sheet data
        """
        try:
            params = {
                "function": "BALANCE_SHEET",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "annualReports" in data and "quarterlyReports" in data:
                reports = data["annualReports"] if annual else data["quarterlyReports"]
                df = pd.DataFrame(reports)
                
                # Convert date columns
                if "fiscalDateEnding" in df.columns:
                    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                    df = df.sort_values("fiscalDateEnding", ascending=False)
                
                return df
            else:
                error_msg = data.get("Error Message", "Unknown error")
                logger.error(f"Error getting balance sheet for {symbol}: {error_msg}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting balance sheet for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="av_cashflow")  # Cache for 1 week
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data from Alpha Vantage API.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing cash flow data
        """
        try:
            params = {
                "function": "CASH_FLOW",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "annualReports" in data and "quarterlyReports" in data:
                reports = data["annualReports"] if annual else data["quarterlyReports"]
                df = pd.DataFrame(reports)
                
                # Convert date columns
                if "fiscalDateEnding" in df.columns:
                    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                    df = df.sort_values("fiscalDateEnding", ascending=False)
                
                return df
            else:
                error_msg = data.get("Error Message", "Unknown error")
                logger.error(f"Error getting cash flow for {symbol}: {error_msg}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting cash flow for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="av_overview")  # Cache for 1 week
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data from Alpha Vantage API.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company overview data
        """
        try:
            params = {
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "Symbol" in data:
                return data
            else:
                error_msg = data.get("Error Message", "Unknown error")
                logger.error(f"Error getting company overview for {symbol}: {error_msg}")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting company overview for {symbol}: {e}")
            return {}
