"""
Finnhub data provider for retrieving financial data.

This module implements the BaseDataProvider interface for Finnhub API.

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
    
    fiscalDateEnding  period     reportedCurrency  totalRevenue   costOfRevenue  grossProfit   operatingExpenses  operatingIncome  netIncome    ebit        ebitda      ...
    2022-12-31        annual     USD              394328000000   223546000000   170782000000  48187000000        119800000000     99803000000  119800000000 135372000000 ...
    2021-12-31        annual     USD              365817000000   212981000000   152836000000  43887000000        108949000000     94680000000  108949000000 123136000000 ...
    ...

get_balance_sheet:
    Returns a DataFrame with balance sheet data:
    
    fiscalDateEnding  period     reportedCurrency  totalAssets   totalCurrentAssets  totalLiabilities  totalCurrentLiabilities  totalShareholderEquity  cash        shortTermInvestments  longTermDebt  ...
    2022-12-31        annual     USD              352755000000  135405000000        302083000000      153982000000             50672000000            23646000000  24658000000           110000000000  ...
    2021-12-31        annual     USD              351002000000  134836000000        287912000000      125481000000             63090000000            17305000000  27699000000           109106000000  ...
    ...

get_cash_flow:
    Returns a DataFrame with cash flow data:
    
    fiscalDateEnding  period     reportedCurrency  operatingCashflow  capitalExpenditures  freeCashflow   dividendPayout  changeInCash  ...
    2022-12-31        annual     USD              122151000000      -11085000000         111066000000   14841000000     480000000     ...
    2021-12-31        annual     USD              104038000000      -11085000000         92953000000    14467000000     -3860000000   ...
    ...

get_company_overview:
    Returns a dictionary with company information:
    {
        'Symbol': 'AAPL',
        'Name': 'Apple Inc',
        'Description': 'Technology',
        'Exchange': 'NASDAQ NMS - GLOBAL MARKET',
        'Industry': 'Technology',
        'Sector': 'Technology',
        'MarketCapitalization': 3019983978000,
        '52WeekHigh': 198.23,
        '52WeekLow': 124.17,
        'PERatio': 31.4,
        'PEGRatio': 2.91,
        'BookValue': 3.835,
        'DividendPerShare': 0.96,
        'DividendYield': 0.0049,
        'EPS': 6.14,
        'ProfitMargin': 0.246,
        'OperatingMarginTTM': 0.3039,
        'ReturnOnAssetsTTM': 0.2223,
        'ReturnOnEquityTTM': 1.566,
        'RevenueTTM': 394328000000,
        'GrossProfitTTM': 0.433,
        'Beta': 1.28
    }
"""
from typing import Dict, List, Union, Any
import pandas as pd
import requests
import finnhub
from datetime import datetime, timedelta
from tqdm import tqdm

from .base import BaseDataProvider
from cache_config import cache
import config
from utils.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

class FinnhubProvider(BaseDataProvider):
    """
    Finnhub data provider for financial data.
    
    Implements the BaseDataProvider interface using Finnhub API.
    """
    
    # API limits
    RATE_LIMIT = 60  # 60 API calls per minute on free tier
    DAILY_LIMIT = None  # No explicit daily limit
    
    def __init__(self, api_key=None):
        """
        Initialize the Finnhub provider.
        
        Args:
            api_key (str, optional): Finnhub API key. If not provided, uses the key from config.
        """
        self.api_key = api_key or config.FINNHUB_API_KEY
        if not self.api_key:
            logger.warning("Finnhub API key not provided")
        
        # Create Finnhub client
        self.client = finnhub.Client(api_key=self.api_key)
    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data using Finnhub API.
        
        Args:
            symbols: Single symbol or list of stock symbols
            period: Time period to retrieve (e.g., '1y', '6m', '1d')
            interval: Data interval (e.g., '1d', '1h', '5m')
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary mapping each symbol to its historical price DataFrame
        """
        if force_refresh:
            cache.delete(self.get_historical_prices, symbols, period, interval)
            
        if isinstance(symbols, str):
            symbols = [symbols]
        
        result = {}
        
        # Convert period to start/end dates
        end_date = datetime.now()
        
        if period == '1d':
            start_date = end_date - timedelta(days=1)
        elif period == '5d':
            start_date = end_date - timedelta(days=5)
        elif period == '1mo':
            start_date = end_date - timedelta(days=30)
        elif period == '3mo':
            start_date = end_date - timedelta(days=90)
        elif period == '6mo':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '2y':
            start_date = end_date - timedelta(days=365*2)
        elif period == '5y':
            start_date = end_date - timedelta(days=365*5)
        elif period == '10y':
            start_date = end_date - timedelta(days=365*10)
        else:
            start_date = end_date - timedelta(days=365)  # Default to 1y
        
        # Convert datetime to Unix timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
          # Convert interval to Finnhub resolution
        if interval == '1d':
            resolution = 'D'
        elif interval == '1h':
            resolution = '60'
        elif interval == '5m':
            resolution = '5'
        elif interval == '15m':
            resolution = '15'
        elif interval == '30m':
            resolution = '30'
        elif interval == '1m':
            resolution = '1'
        else:
            resolution = 'D'  # Default to daily
        
        # Use tqdm to show a progress bar when processing multiple symbols
        for symbol in tqdm(symbols, desc="Fetching Finnhub prices", disable=len(symbols) <= 1):
            try:
                candles = self.client.stock_candles(symbol, resolution, start_timestamp, end_timestamp)
                
                if candles['s'] == 'ok' and len(candles['t']) > 0:
                    df = pd.DataFrame({
                        'Date': pd.to_datetime(candles['t'], unit='s'),
                        'Open': candles['o'],
                        'High': candles['h'],
                        'Low': candles['l'],
                        'Close': candles['c'],
                        'Volume': candles['v']
                    })
                    
                    # Set Date as index
                    df = df.set_index('Date')
                    
                    # Sort by date
                    df = df.sort_index()
                    
                    result[symbol] = df
                else:
                    logger.error(f"Error getting price data for {symbol}: {candles.get('s', 'Unknown error')}")
            
            except Exception as e:
                logger.error(f"Error getting price data for {symbol}: {e}")
        
        return result
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    def get_income_statement(self, symbol: str, 
                            annual: bool = True,
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        Get income statement data from Finnhub API.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing income statement data
        """
        if force_refresh:
            cache.delete(self.get_income_statement, symbol, annual)
            
        try:
            freq = "annual" if annual else "quarterly"
            financials = self.client.company_basic_financials(symbol, 'all')
            
            if 'financials' in financials and 'ic' in financials['financials']:
                income_data = []
                
                for period in financials['financials']['ic']:
                    if period['period'] == freq:
                        income_data.append(period)
                
                if income_data:
                    df = pd.DataFrame(income_data)
                    
                    # Rename date column to match our standard format
                    df = df.rename(columns={"year": "fiscalDateEnding"})
                    
                    # Convert date to datetime
                    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                    
                    # Sort by date
                    df = df.sort_values("fiscalDateEnding", ascending=False)
                    
                    # Rename columns to match Alpha Vantage format
                    column_mapping = {
                        "totalRevenue": "totalRevenue",
                        "costOfRevenue": "costOfRevenue",
                        "grossProfit": "grossProfit",
                        "totalOperatingExpenses": "operatingExpenses",
                        "operatingIncome": "operatingIncome",
                        "netIncome": "netIncome",
                        "ebit": "ebit",
                        "ebitda": "ebitda"
                    }
                    
                    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                    
                    return df
                else:
                    logger.warning(f"No {freq} income statement data found for {symbol}")
                    return pd.DataFrame()
            else:
                logger.error(f"Error getting income statement for {symbol}: {financials.get('error', 'Unknown error')}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting income statement for {symbol}: {e}")
            return pd.DataFrame()
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data from Finnhub API.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing balance sheet data
        """
        if force_refresh:
            cache.delete(self.get_balance_sheet, symbol, annual)
            
        try:
            freq = "annual" if annual else "quarterly"
            financials = self.client.company_basic_financials(symbol, 'all')
            
            if 'financials' in financials and 'bs' in financials['financials']:
                balance_data = []
                
                for period in financials['financials']['bs']:
                    if period['period'] == freq:
                        balance_data.append(period)
                
                if balance_data:
                    df = pd.DataFrame(balance_data)
                    
                    # Rename date column to match our standard format
                    df = df.rename(columns={"year": "fiscalDateEnding"})
                    
                    # Convert date to datetime
                    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                    
                    # Sort by date
                    df = df.sort_values("fiscalDateEnding", ascending=False)
                    
                    # Rename columns to match Alpha Vantage format
                    column_mapping = {
                        "totalAssets": "totalAssets",
                        "totalCurrentAssets": "totalCurrentAssets",
                        "totalLiabilities": "totalLiabilities",
                        "totalCurrentLiabilities": "totalCurrentLiabilities",
                        "totalEquity": "totalShareholderEquity",
                        "cashAndEquivalents": "cash",
                        "shortTermInvestments": "shortTermInvestments",
                        "longTermDebt": "longTermDebt"
                    }
                    
                    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                    
                    return df
                else:
                    logger.warning(f"No {freq} balance sheet data found for {symbol}")
                    return pd.DataFrame()
            else:
                logger.error(f"Error getting balance sheet for {symbol}: {financials.get('error', 'Unknown error')}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting balance sheet for {symbol}: {e}")
            return pd.DataFrame()
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data from Finnhub API.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing cash flow data
        """
        if force_refresh:
            cache.delete(self.get_cash_flow, symbol, annual)
            
        try:
            freq = "annual" if annual else "quarterly"
            financials = self.client.company_basic_financials(symbol, 'all')
            
            if 'financials' in financials and 'cf' in financials['financials']:
                cash_flow_data = []
                
                for period in financials['financials']['cf']:
                    if period['period'] == freq:
                        cash_flow_data.append(period)
                
                if cash_flow_data:
                    df = pd.DataFrame(cash_flow_data)
                    
                    # Rename date column to match our standard format
                    df = df.rename(columns={"year": "fiscalDateEnding"})
                    
                    # Convert date to datetime
                    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                    
                    # Sort by date
                    df = df.sort_values("fiscalDateEnding", ascending=False)
                    
                    # Rename columns to match Alpha Vantage format
                    column_mapping = {
                        "cashFromOperations": "operatingCashflow",
                        "capitalExpenditure": "capitalExpenditures",
                        "freeCashFlow": "freeCashflow",
                        "dividendsPaid": "dividendPayout",
                        "netChangeInCash": "changeInCash"
                    }
                    
                    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                    
                    return df
                else:
                    logger.warning(f"No {freq} cash flow data found for {symbol}")
                    return pd.DataFrame()
            else:
                logger.error(f"Error getting cash flow for {symbol}: {financials.get('error', 'Unknown error')}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting cash flow for {symbol}: {e}")
            return pd.DataFrame()
    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data from Finnhub API.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company overview data
        """
        if force_refresh:
            cache.delete(self.get_company_overview, symbol)
            
        try:
            # Get company profile
            profile = self.client.company_profile2(symbol=symbol)
            
            # Get basic financials
            financials = self.client.company_basic_financials(symbol, 'all')
            
            # Get quotes
            quote = self.client.quote(symbol)
            
            # Convert to standardized format similar to Alpha Vantage
            overview = {}
            
            # Symbol and company name from profile
            overview['Symbol'] = profile.get('ticker', symbol)
            overview['Name'] = profile.get('name', '')
            overview['Description'] = profile.get('finnhubIndustry', '')
            overview['Exchange'] = profile.get('exchange', '')
            overview['Industry'] = profile.get('finnhubIndustry', '')
            overview['Sector'] = profile.get('finnhubIndustry', '')  # Finnhub doesn't provide separate sector
            
            # Market data from quote
            overview['MarketCapitalization'] = profile.get('marketCapitalization', '') * 1000000 if profile.get('marketCapitalization') else ''
            overview['52WeekHigh'] = quote.get('h', '')
            overview['52WeekLow'] = quote.get('l', '')
            
            # Financial metrics from financials
            if 'metric' in financials:
                metrics = financials['metric']
                overview['PERatio'] = metrics.get('peBasicExclExtraTTM', '')
                overview['PEGRatio'] = metrics.get('pegRatioTTM', '')
                overview['BookValue'] = metrics.get('bookValuePerShareAnnual', '')
                overview['DividendPerShare'] = metrics.get('dividendPerShareAnnual', '')
                overview['DividendYield'] = metrics.get('dividendYieldIndicatedAnnual', '')
                overview['EPS'] = metrics.get('epsBasicExclExtraItemsTTM', '')
                overview['ProfitMargin'] = metrics.get('netProfitMarginTTM', '')
                overview['OperatingMarginTTM'] = metrics.get('operatingMarginTTM', '')
                overview['ReturnOnAssetsTTM'] = metrics.get('roaTTM', '')
                overview['ReturnOnEquityTTM'] = metrics.get('roeTTM', '')
                overview['RevenueTTM'] = metrics.get('revenueTTM', '')
                overview['GrossProfitTTM'] = metrics.get('grossMarginTTM', '')
                overview['Beta'] = metrics.get('beta', '')
                
            return overview
        
        except Exception as e:
            logger.error(f"Error getting company overview for {symbol}: {e}")
            return {}
