"""
Financial Modeling Prep data provider for retrieving financial data.

This module implements the BaseDataProvider interface for Financial Modeling Prep API.

Example Responses
----------------

get_historical_prices:
    Returns a dictionary where keys are symbols and values are DataFrames:
    {
        'AAPL': DataFrame(
            Date        Open      High       Low      Close     Volume
            2023-01-03  130.28    130.90     124.17   125.07    111019584
            2023-01-04  127.13    128.66     125.08   126.36    70790742
            ...
        )
    }
    
    Each DataFrame contains columns: Open, High, Low, Close, Volume

get_income_statement:
    Returns a DataFrame with financial statement data:
    
    fiscalDateEnding  symbol  reportedCurrency  cik    fillingDate  acceptedDate    calendarYear  period  revenue        costOfRevenue  grossProfit    totalRevenue   operatingExpenses  operatingIncome  netIncome     ...
    2022-09-30        AAPL    USD              320193  2022-10-28   2022-10-28      2022         FY      394328000000   223546000000   170782000000   394328000000   48187000000        119800000000     99803000000   ...
    2021-09-30        AAPL    USD              320193  2021-10-29   2021-10-29      2021         FY      365817000000   212981000000   152836000000   365817000000   43887000000        108949000000     94680000000   ...
    ...

get_balance_sheet:
    Returns a DataFrame with balance sheet data:
    
    fiscalDateEnding  symbol  reportedCurrency  cik    fillingDate  acceptedDate    calendarYear  period  cashAndCashEquivalents  shortTermInvestments  totalCurrentAssets  totalAssets   totalCurrentLiabilities  totalLiabilities  totalShareholderEquity  ...
    2022-09-30        AAPL    USD              320193  2022-10-28   2022-10-28      2022         FY      23646000000            24658000000          135405000000       352755000000  153982000000             302083000000      50672000000           ...
    2021-09-30        AAPL    USD              320193  2021-10-29   2021-10-29      2021         FY      17305000000            27699000000          134836000000       351002000000  125481000000             287912000000      63090000000           ...
    ...

get_cash_flow:
    Returns a DataFrame with cash flow data:
    
    fiscalDateEnding  symbol  reportedCurrency  cik    fillingDate  acceptedDate    calendarYear  period  netIncome   operatingCashflow  capitalExpenditures  freeCashFlow   dividendPayout  changeInCash  repurchaseOfStock  issuanceOfStock  ...
    2022-09-30        AAPL    USD              320193  2022-10-28   2022-10-28      2022         FY      99803000000  122151000000      -11085000000        111066000000   14841000000     480000000      89402000000        4800000000       ...
    2021-09-30        AAPL    USD              320193  2021-10-29   2021-10-29      2021         FY      94680000000  104038000000      -11085000000        92953000000    14467000000     -3860000000    85971000000        1105000000       ...
    ...

get_company_overview:
    Returns a dictionary with company information:
    {
        'Symbol': 'AAPL', 
        'Name': 'Apple Inc',
        'Description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide...',
        'Exchange': 'NASDAQ',
        'Sector': 'Technology',
        'Industry': 'Consumer Electronics',
        'MarketCapitalization': 3019983978000,
        'PERatio': 31.4,
        'EPS': 6.14,
        'Beta': 1.28,
        '52WeekHigh': '198.23',
        '52WeekLow': '124.17',
        'LastDividendDate': '2023-05-12',
        'PriceToBookRatio': 49.7,
        'PriceToSalesRatio': 7.65,
        'SharesOutstanding': 15634232000,
        'ReturnOnEquityTTM': 1.566,
        'ReturnOnAssetsTTM': 0.2223,
        'ProfitMargin': 0.246,
        'OperatingMarginTTM': 0.3039,
        'DebtToEquityRatio': 1.86,
        'EVToEBITDA': 18.4
    }
"""
from typing import Dict, List, Union, Any
import pandas as pd
import requests
import functools
from tqdm import tqdm  # For progress bars

from .base import BaseDataProvider
from cache_config import cache
import config
from utils.logger import get_logger
from utils.rate_limiter import RateLimiter

# Get logger for this module
logger = get_logger(__name__)

# Get rate limiter instance for Financial Modeling Prep
fmp_rate_limiter = RateLimiter.get_instance("financial_modeling_prep")

class FinancialModelingPrepProvider(BaseDataProvider):
    """
    Financial Modeling Prep data provider for financial data.
    
    Implements the BaseDataProvider interface using Financial Modeling Prep API.
    Uses paid tier with no daily request limits.
    Rate limiting is still applied to stay within per-minute limits.
    """
    
    # API limits
    RATE_LIMIT = config.API_RATE_LIMITS["financial_modeling_prep"]  # 300 calls per minute
    DAILY_LIMIT = config.API_DAILY_LIMITS["financial_modeling_prep"]  # None - paid tier with no daily limit
    
    def __init__(self, api_key=None):
        """
        Initialize the Financial Modeling Prep provider.
        
        Args:
            api_key (str, optional): FMP API key. If not provided, uses the key from config.
        """
        self.api_key = api_key or config.FINANCIAL_MODELING_PREP_API_KEY
        if not self.api_key:
            logger.warning("Financial Modeling Prep API key not provided")
        
        # Base URL for FMP API
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data using Financial Modeling Prep API.
        
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
        
        # Map period to days parameter
        days_map = {
            "1d": "1",
            "5d": "5",
            "1mo": "30",
            "3mo": "90",
            "6mo": "180",
            "1y": "365",
            "2y": "730",            "5y": "1825",
            "max": "5000"  # Using a large number for max
        }
        days = days_map.get(period, "365")  # Default to 1 year
        
        # Use tqdm to show a progress bar when processing multiple symbols
        for symbol in tqdm(symbols, desc="Fetching historical prices", disable=len(symbols) <= 1):
            try:
                url = f"{self.base_url}/historical-price-full/{symbol}"
                params = {"apikey": self.api_key, "timeseries": days}
                
                # Apply rate limiting before API call
                fmp_rate_limiter.wait_if_needed()
                response = requests.get(url, params=params)
                data = response.json()
                
                if "historical" in data:
                    historical = data["historical"]
                    df = pd.DataFrame(historical)
                    
                    # Rename columns to match our standard format
                    df = df.rename(columns={
                        "date": "Date",
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume"
                    })
                    
                    # Convert date to datetime and set as index
                    df["Date"] = pd.to_datetime(df["Date"])
                    df = df.set_index("Date")
                    
                    # Sort by date
                    df = df.sort_index()
                    
                    # Select only the standard columns
                    df = df[["Open", "High", "Low", "Close", "Volume"]]
                    
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
        Get income statement data from Financial Modeling Prep API.
        
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
            period = "annual" if annual else "quarter"
            url = f"{self.base_url}/income-statement/{symbol}"
            params = {"apikey": self.api_key, "period": period, "limit": 5}
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                
                # Rename date column to match our standard format
                df = df.rename(columns={"date": "fiscalDateEnding"})
                
                # Convert date to datetime
                df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                
                # Sort by date
                df = df.sort_values("fiscalDateEnding", ascending=False)
                
                # Rename some columns to match Alpha Vantage format
                column_mapping = {
                    "revenue": "totalRevenue",
                    "costOfRevenue": "costOfRevenue",
                    "grossProfit": "grossProfit",
                    "grossProfitRatio": "grossProfitMargin",
                    "operatingExpenses": "operatingExpenses",
                    "operatingIncome": "operatingIncome",
                    "netIncome": "netIncome",
                    "ebitda": "ebitda"
                }
                
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                return df
            else:
                logger.error(f"Error getting income statement for {symbol}: {data}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting income statement for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data from Financial Modeling Prep API.
        
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
            period = "annual" if annual else "quarter"
            url = f"{self.base_url}/balance-sheet-statement/{symbol}"
            params = {"apikey": self.api_key, "period": period, "limit": 5}
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                
                # Rename date column to match our standard format
                df = df.rename(columns={"date": "fiscalDateEnding"})
                
                # Convert date to datetime
                df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                
                # Sort by date
                df = df.sort_values("fiscalDateEnding", ascending=False)
                
                # Rename some columns to match Alpha Vantage format
                column_mapping = {
                    "totalAssets": "totalAssets",
                    "totalCurrentAssets": "totalCurrentAssets",
                    "totalLiabilities": "totalLiabilities",
                    "totalCurrentLiabilities": "totalCurrentLiabilities",
                    "totalStockholdersEquity": "totalShareholderEquity",
                    "cashAndCashEquivalents": "cash",
                    "shortTermInvestments": "shortTermInvestments",
                    "longTermDebt": "longTermDebt",
                    "commonStock": "commonStock"
                }
                
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                return df
            else:
                logger.error(f"Error getting balance sheet for {symbol}: {data}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting balance sheet for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data from Financial Modeling Prep API.
        
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
            period = "annual" if annual else "quarter"
            url = f"{self.base_url}/cash-flow-statement/{symbol}"
            params = {"apikey": self.api_key, "period": period, "limit": 5}
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                
                # Rename date column to match our standard format
                df = df.rename(columns={"date": "fiscalDateEnding"})
                
                # Convert date to datetime
                df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
                
                # Sort by date
                df = df.sort_values("fiscalDateEnding", ascending=False)
                
                # Rename some columns to match Alpha Vantage format
                column_mapping = {
                    "netCashProvidedByOperatingActivities": "operatingCashflow",
                    "capitalExpenditure": "capitalExpenditures",
                    "freeCashFlow": "freeCashflow",
                    "dividendsPaid": "dividendPayout",
                    "netChangeInCash": "changeInCash",
                    "stockRepurchased": "repurchaseOfStock",
                    "commonStockIssued": "issuanceOfStock"
                }
                
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                return df
            else:
                logger.error(f"Error getting cash flow for {symbol}: {data}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting cash flow for {symbol}: {e}")
            return pd.DataFrame()

    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data from Financial Modeling Prep API.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company profile and metrics
        """
        if force_refresh:
            cache.delete(self.get_company_overview, symbol)
        
        try:
            url = f"{self.base_url}/profile/{symbol}"
            params = {"apikey": self.api_key}
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                profile = data[0]
                
                # Convert to standardized format similar to Alpha Vantage
                overview = {}
                
                # Symbol and company name
                overview['Symbol'] = profile.get('symbol', symbol)
                overview['Name'] = profile.get('companyName', '')
                overview['Description'] = profile.get('description', '')
                overview['Exchange'] = profile.get('exchange', '')
                overview['Sector'] = profile.get('sector', '')
                overview['Industry'] = profile.get('industry', '')
                
                # Financial metrics
                overview['MarketCapitalization'] = profile.get('mktCap', '')
                overview['PERatio'] = profile.get('pe', '')
                overview['EPS'] = profile.get('eps', '')
                overview['Beta'] = profile.get('beta', '')
                overview['52WeekHigh'] = profile.get('range', '').split('-')[1].strip() if '-' in profile.get('range', '') else ''
                overview['52WeekLow'] = profile.get('range', '').split('-')[0].strip() if '-' in profile.get('range', '') else ''
                overview['LastDividendDate'] = profile.get('lastDiv', '')
                overview['PriceToBookRatio'] = profile.get('priceToBookRatio', '')
                overview['PriceToSalesRatio'] = profile.get('priceToSalesRatio', '')
                overview['SharesOutstanding'] = profile.get('sharesOutstanding', '')
                
                # Get additional financial ratios
                try:
                    ratios_url = f"{self.base_url}/ratios/{symbol}"
                    ratios_response = requests.get(ratios_url, params=params)
                    ratios_data = ratios_response.json()
                    
                    if isinstance(ratios_data, list) and len(ratios_data) > 0:
                        ratio = ratios_data[0]
                        overview['ReturnOnEquityTTM'] = ratio.get('returnOnEquity', '')
                        overview['ReturnOnAssetsTTM'] = ratio.get('returnOnAssets', '')
                        overview['ProfitMargin'] = ratio.get('netProfitMargin', '')
                        overview['OperatingMarginTTM'] = ratio.get('operatingProfitMargin', '')
                        overview['DebtToEquityRatio'] = ratio.get('debtToEquity', '')
                        overview['EVToEBITDA'] = ratio.get('enterpriseValueMultiple', '')
                except Exception as e:
                    logger.warning(f"Error getting financial ratios for {symbol}: {e}")
                
                return overview
            else:
                logger.error(f"Error getting company overview for {symbol}: {data}")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting company overview for {symbol}: {e}")
            return {}
