"""
Yahoo Finance data provider for retrieving financial data.

This module implements the BaseDataProvider interface for yfinance.

Example Responses
----------------

get_historical_prices:
    Returns a dictionary where keys are symbols and values are DataFrames:
    {
        'AAPL': DataFrame(
            Date        Open      High       Low     Close    Volume  Dividends  Stock Splits
            2023-01-03  125.07    130.90    124.17   125.07   111019584  0.0      0.0
            2023-01-04  126.89    128.66    125.08   126.36   70790742   0.0      0.0
            ...
        )
    }
    
    Note: For multiple symbols, yfinance may return MultiIndex DataFrames.
    Each DataFrame contains columns: Open, High, Low, Close, Volume, Dividends, Stock Splits

get_income_statement:
    Returns a DataFrame with financial statement data:
    
    fiscalDateEnding  totalRevenue  costOfRevenue  grossProfit  operatingExpenses  operatingIncome  netIncome  ebit      ebitda
    2022-09-30        394328000000  223546000000   170782000000  48187000000        119800000000     99803000000  119800000000  135372000000
    2021-09-30        365817000000  212981000000   152836000000  43887000000        108949000000     94680000000  108949000000  123136000000
    ...

get_balance_sheet:
    Returns a DataFrame with balance sheet data:
    
    fiscalDateEnding  totalAssets   totalCurrentAssets  totalLiabilities  totalCurrentLiabilities  totalShareholderEquity  cash        shortTermInvestments  longTermDebt  commonStock
    2022-09-30        352755000000  135405000000        302083000000      153982000000            50672000000            23646000000  24658000000            110000000000  64849000000
    2021-09-30        351002000000  134836000000        287912000000      125481000000            63090000000            17305000000  27699000000            109106000000  57365000000
    ...

get_cash_flow:
    Returns a DataFrame with cash flow data:
    
    fiscalDateEnding  operatingCashflow  capitalExpenditures  freeCashflow   dividendPayout  netBorrowings  netIncome    changeInCash  repurchaseOfStock  issuanceOfStock
    2022-09-30        122151000000      -11085000000         111066000000   14841000000     -9543000000    99803000000   480000000     89402000000        4800000000  
    2021-09-30        104038000000      -11085000000         92953000000    14467000000     12665000000    94680000000   -3860000000   85971000000        1105000000
    ...

get_company_overview:
    Returns a dictionary with company information:
    {
        'Symbol': 'AAPL', 
        'Name': 'Apple Inc.',
        'Description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide...',
        'Exchange': 'NASDAQ',
        'Sector': 'Technology',
        'Industry': 'Consumer Electronics',
        'MarketCapitalization': 2900000000000,
        'EBITDA': 135372000000,
        'PERatio': 29.12,
        'PEGRatio': 2.85,
        'BookValue': 3.73,
        'DividendPerShare': 0.92,
        'DividendYield': 0.0050,
        'EPS': 6.11,
        'ProfitMargin': 0.2531,
        'OperatingMarginTTM': 0.3039,
        ...
    }
"""
from typing import Dict, List, Union, Any
import pandas as pd
import yfinance as yf
import logging

from .base import BaseDataProvider
from cache_manager import cache_api_call
from utils.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

class YFinanceProvider(BaseDataProvider):
    """
    Yahoo Finance data provider for financial data.
    
    Implements the BaseDataProvider interface using yfinance.
    """
    
    # No explicit API limits for yfinance, but being reasonable
    RATE_LIMIT = None
    DAILY_LIMIT = None
    
    def __init__(self):
        """Initialize the Yahoo Finance provider."""
        pass
    
    @cache_api_call(expiry_hours=24, cache_key_prefix="yf_prices")
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data using yfinance.
        
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
        
        try:
            # Download data for all symbols at once (more efficient)
            data = yf.download(
                tickers=symbols,
                period=period,
                interval=interval,
                group_by='ticker',
                auto_adjust=True,
                progress=False
            )
            
            # If only one symbol is requested, yfinance returns a different format
            if len(symbols) == 1:
                result[symbols[0]] = data
            else:
                # For multiple symbols, organize by ticker
                for symbol in symbols:
                    if symbol in data.columns.levels[0]:
                        result[symbol] = data[symbol].copy()
            
            logger.info(f"Successfully retrieved historical prices for {len(result)} symbols")
            return result
        
        except Exception as e:
            logger.error(f"Error fetching historical prices: {e}")
            return {}
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="yf_income")  # Cache for 1 week
    def get_income_statement(self, symbol: str, 
                            annual: bool = True,
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        Get income statement data using yfinance.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing income statement data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get financials
            if annual:
                income_stmt = ticker.income_stmt
            else:
                income_stmt = ticker.quarterly_income_stmt
            
            if income_stmt is not None and not income_stmt.empty:
                # Convert to standardized format similar to Alpha Vantage
                df = income_stmt.T.reset_index()
                df = df.rename(columns={'index': 'fiscalDateEnding'})
                
                # Convert date to datetime
                df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
                
                # Rename columns to match Alpha Vantage format
                column_mapping = {
                    'Total Revenue': 'totalRevenue',
                    'Cost Of Revenue': 'costOfRevenue',
                    'Gross Profit': 'grossProfit',
                    'Operating Expense': 'operatingExpenses',
                    'Operating Income': 'operatingIncome',
                    'Net Income': 'netIncome',
                    'EBIT': 'ebit',
                    'EBITDA': 'ebitda'
                }
                
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                return df
            else:
                logger.warning(f"No income statement data found for {symbol}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting income statement for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="yf_balance")  # Cache for 1 week
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data using yfinance.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing balance sheet data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get balance sheet
            if annual:
                balance_sheet = ticker.balance_sheet
            else:
                balance_sheet = ticker.quarterly_balance_sheet
            
            if balance_sheet is not None and not balance_sheet.empty:
                # Convert to standardized format similar to Alpha Vantage
                df = balance_sheet.T.reset_index()
                df = df.rename(columns={'index': 'fiscalDateEnding'})
                
                # Convert date to datetime
                df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
                
                # Rename columns to match Alpha Vantage format
                column_mapping = {
                    'Total Assets': 'totalAssets',
                    'Total Current Assets': 'totalCurrentAssets',
                    'Total Liabilities': 'totalLiabilities',
                    'Total Current Liabilities': 'totalCurrentLiabilities',
                    'Total Stockholder Equity': 'totalShareholderEquity',
                    'Cash': 'cash',
                    'Short Term Investments': 'shortTermInvestments',
                    'Long Term Debt': 'longTermDebt',
                    'Common Stock': 'commonStock'
                }
                
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                return df
            else:
                logger.warning(f"No balance sheet data found for {symbol}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting balance sheet for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache_api_call(expiry_hours=168, cache_key_prefix="yf_cashflow")  # Cache for 1 week
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data using yfinance.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing cash flow data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get cash flow
            if annual:
                cash_flow = ticker.cashflow
            else:
                cash_flow = ticker.quarterly_cashflow
            
            if cash_flow is not None and not cash_flow.empty:
                # Convert to standardized format similar to Alpha Vantage
                df = cash_flow.T.reset_index()
                df = df.rename(columns={'index': 'fiscalDateEnding'})
                
                # Convert date to datetime
                df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
                
                # Rename columns to match Alpha Vantage format
                column_mapping = {
                    'Operating Cash Flow': 'operatingCashflow',
                    'Capital Expenditure': 'capitalExpenditures',
                    'Free Cash Flow': 'freeCashflow',
                    'Dividend Paid': 'dividendPayout',
                    'Net Borrowings': 'netBorrowings',
                    'Net Income': 'netIncome',
                    'Change In Cash': 'changeInCash',
                    'Repurchase Of Stock': 'repurchaseOfStock',
                    'Issuance Of Stock': 'issuanceOfStock'
                }
                
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                return df
            else:
                logger.warning(f"No cash flow data found for {symbol}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error getting cash flow for {symbol}: {e}")
            return pd.DataFrame()
    
    @cache_api_call(expiry_hours=24, cache_key_prefix="yf_overview")
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data using yfinance.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company overview data
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if info:
                # Convert to standardized format similar to Alpha Vantage
                overview = {}
                
                # Symbol and company name
                overview['Symbol'] = info.get('symbol', symbol)
                overview['Name'] = info.get('shortName', '')
                overview['Description'] = info.get('longBusinessSummary', '')
                overview['Exchange'] = info.get('exchange', '')
                overview['Sector'] = info.get('sector', '')
                overview['Industry'] = info.get('industry', '')
                
                # Financial metrics
                overview['MarketCapitalization'] = info.get('marketCap', '')
                overview['EBITDA'] = info.get('ebitda', '')
                overview['PERatio'] = info.get('trailingPE', '')
                overview['PEGRatio'] = info.get('pegRatio', '')
                overview['BookValue'] = info.get('bookValue', '')
                overview['DividendPerShare'] = info.get('dividendRate', '')
                overview['DividendYield'] = info.get('dividendYield', '')
                overview['EPS'] = info.get('trailingEps', '')
                overview['ProfitMargin'] = info.get('profitMargins', '')
                overview['OperatingMarginTTM'] = info.get('operatingMargins', '')
                overview['ReturnOnAssetsTTM'] = info.get('returnOnAssets', '')
                overview['ReturnOnEquityTTM'] = info.get('returnOnEquity', '')
                overview['RevenueTTM'] = info.get('totalRevenue', '')
                overview['GrossProfitTTM'] = info.get('grossProfits', '')
                overview['RevenuePerShareTTM'] = info.get('revenuePerShare', '')
                overview['Beta'] = info.get('beta', '')
                overview['52WeekHigh'] = info.get('fiftyTwoWeekHigh', '')
                overview['52WeekLow'] = info.get('fiftyTwoWeekLow', '')
                overview['50DayMovingAverage'] = info.get('fiftyDayAverage', '')
                overview['200DayMovingAverage'] = info.get('twoHundredDayAverage', '')
                overview['SharesOutstanding'] = info.get('sharesOutstanding', '')
                
                return overview
            else:
                logger.warning(f"No company overview data found for {symbol}")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting company overview for {symbol}: {e}")
            return {}
