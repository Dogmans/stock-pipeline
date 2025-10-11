"""
Alpha Vantage data provider for retrieving financial data.

This module implements the BaseDataProvider interface for Alpha Vantage API.

Example Responses
----------------

get_historical_prices:
    Returns a dictionary where keys are symbols and values are DataFrames:
    {
        'AAPL': DataFrame(
            Date        Open      High       Low      Close    Volume
            2023-01-03  130.28    130.90     124.17   125.07   111019584
            2023-01-04  127.13    128.66     125.08   126.36   70790742
            ...
        )
    }
    
    Each DataFrame contains columns: Open, High, Low, Close, Volume

get_income_statement:
    Returns a DataFrame with financial statement data:
    
    fiscalDateEnding  reportedCurrency  grossProfit   totalRevenue   costOfRevenue  ...  netIncome  ebitda      ebit        ...
    2022-09-30        USD              170782000000   394328000000   223546000000   ...  99803000000 135372000000 119800000000 ...
    2021-09-30        USD              152836000000   365817000000   212981000000   ...  94680000000 123136000000 108949000000 ...
    ...

get_balance_sheet:
    Returns a DataFrame with balance sheet data:
    
    fiscalDateEnding  reportedCurrency  totalAssets   totalCurrentAssets  ...  totalShareholderEquity  commonStockSharesOutstanding  ...
    2022-09-30        USD              352755000000   135405000000        ...  50672000000            15908118000                   ...
    2021-09-30        USD              351002000000   134836000000        ...  63090000000            16426786000                   ...
    ...

get_cash_flow:
    Returns a DataFrame with cash flow data:
    
    fiscalDateEnding  reportedCurrency  operatingCashflow  capitalExpenditures  ...  dividendPayout  netIncome    ...
    2022-09-30        USD              122151000000      -11085000000          ...  14841000000     99803000000   ...
    2021-09-30        USD              104038000000      -11085000000          ...  14467000000     94680000000   ...
    ...

get_company_overview:
    Returns a dictionary with company information:
    {
        'Symbol': 'AAPL',
        'AssetType': 'Common Stock',
        'Name': 'Apple Inc',
        'Description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide...',
        'CIK': '320193',
        'Exchange': 'NASDAQ',
        'Currency': 'USD',
        'Country': 'USA',
        'Sector': 'Technology',
        'Industry': 'Consumer Electronics',
        'Address': 'One Apple Park Way, Cupertino, CA, United States, 95014',
        'FiscalYearEnd': 'September',
        'LatestQuarter': '2023-06-30',
        'MarketCapitalization': '3019983978000',
        'EBITDA': '126330004000',
        'PERatio': '31.4',
        'PEGRatio': '2.91',
        'BookValue': '3.835',
        'DividendPerShare': '0.96',
        'DividendYield': '0.0049',
        'EPS': '6.14',
        'RevenuePerShareTTM': '25.01',
        'ProfitMargin': '0.246',
        '52WeekHigh': '198.23',
        '52WeekLow': '124.17',
        ...
    }
"""
from typing import Dict, List, Union, Any
import pandas as pd
import requests
import os
from tqdm import tqdm

from .base import BaseDataProvider
from cache_config import cache, clear_all_cache

import config
from utils.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

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
    @cache.memoize(expire=24*3600)  # Cache for 24 hours
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
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
            
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
        
        # Use tqdm to show a progress bar when processing multiple symbols
        for symbol in tqdm(symbols, desc="Fetching Alpha Vantage prices", disable=len(symbols) <= 1):
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
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
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
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
            
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
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
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
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
            
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
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
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
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
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
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
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
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
            
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
