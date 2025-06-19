"""
Yahoo Finance data provider for retrieving financial data.

This module implements the BaseDataProvider interface for yfinance.
"""
from typing import Dict, List, Union, Any
import pandas as pd
import yfinance as yf
import logging

from .base import BaseDataProvider
from cache_manager import cache_api_call
from utils.logger import setup_logging

# Set up logger for this module
logger = setup_logging()

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
