"""
Financial Modeling Prep data provider for retrieving financial data.

This module implements the BaseDataProvider interface for Financial Modeling Prep API.
"""
from typing import Dict, List, Union, Any
import pandas as pd
import requests
import logging

from .base import BaseDataProvider
from cache_manager import cache_api_call
import config
from utils import setup_logging

# Set up logger for this module
logger = setup_logging()

class FinancialModelingPrepProvider(BaseDataProvider):
    """
    Financial Modeling Prep data provider for financial data.
    
    Implements the BaseDataProvider interface using Financial Modeling Prep API.
    """
    
    # API limits
    RATE_LIMIT = None  # No explicit rate limit mentioned
    DAILY_LIMIT = 250  # 250 requests per day on free tier
    
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
    
    @cache_api_call(expiry_hours=24, cache_key_prefix="fmp_prices")
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
            "2y": "730",
            "5y": "1825",
            "max": "5000"  # Using a large number for max
        }
        days = days_map.get(period, "365")  # Default to 1 year
        
        for symbol in symbols:
            try:
                url = f"{self.base_url}/historical-price-full/{symbol}"
                params = {"apikey": self.api_key, "timeseries": days}
                
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
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="fmp_income")  # Cache for 1 week
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
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="fmp_balance")  # Cache for 1 week
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
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="fmp_cashflow")  # Cache for 1 week
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
    
    @cache_api_call(expiry_hours=24, cache_key_prefix="fmp_overview")
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data from Financial Modeling Prep API.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company overview data
        """
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
