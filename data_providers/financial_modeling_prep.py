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
from utils.throttling import throttler, create_cache_checker

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
    
    def _make_api_request(self, endpoint, symbol, params=None, rate_limit=True):
        """
        Make an API request to Financial Modeling Prep.
        
        Args:
            endpoint (str): API endpoint path (without base URL)
            symbol (str): Stock symbol to query
            params (dict, optional): Additional query parameters
            rate_limit (bool): Whether to apply rate limiting
            
        Returns:
            tuple: (success (bool), data (dict/list), error_msg (str or None))
        """
        url = f"{self.base_url}/{endpoint}/{symbol}"
        
        # Initialize params dictionary if None
        if params is None:
            params = {}
        
        # Always include API key
        params["apikey"] = self.api_key
        
        try:
            # Apply legacy rate limiting if requested (cache-aware throttling is handled by decorators)
            if rate_limit:
                fmp_rate_limiter.wait_if_needed()
                
            # Make the request
            response = requests.get(url, params=params)
            
            # Check if response is successful
            if response.status_code == 200:
                data = response.json()
                
                # Check if data is valid (list with content for most endpoints)
                if isinstance(data, list) and len(data) > 0:
                    return True, data, None
                elif not isinstance(data, list) and isinstance(data, dict):
                    # Some endpoints return direct dictionaries
                    return True, data, None
                else:
                    error_msg = f"Empty or invalid response: {data}"
                    logger.error(f"API error for {url}: {error_msg}")
                    return False, None, error_msg
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"API error for {url}: {error_msg}")
                return False, None, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Exception during API call to {url}: {error_msg}")
            return False, None, error_msg
    
    def _process_financial_statement(self, data, column_mapping=None):
        """
        Process financial statement data into standardized DataFrame.
        
        Args:
            data (list): Raw financial statement data from API
            column_mapping (dict, optional): Column name mapping
            
        Returns:
            pd.DataFrame: Processed financial statement data
        """
        if not data:
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Rename date column to match our standard format
        df = df.rename(columns={"date": "fiscalDateEnding"})
        
        # Convert date to datetime
        df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
        
        # Sort by date
        df = df.sort_values("fiscalDateEnding", ascending=False)
        
        # Rename columns if mapping provided
        if column_mapping:
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        return df
    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, lambda self, symbols, period="1y", interval="1d", force_refresh=False: f"FinancialModelingPrepProvider.get_historical_prices:{symbols}:{period}:{interval}:{force_refresh}"
    ))
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
            "2y": "730",
            "5y": "1825",
            "max": "5000"  # Using a large number for max
        }
        days = days_map.get(period, "365")  # Default to 1 year
        
        # Use tqdm to show a progress bar when processing multiple symbols
        for symbol in tqdm(symbols, desc="Fetching historical prices", disable=len(symbols) <= 1):
            # Set up parameters for this symbol
            params = {"timeseries": days}
            
            # Make API request
            success, data, error = self._make_api_request(
                endpoint="historical-price-full",
                symbol=symbol,
                params=params
            )
            
            if not success:
                logger.error(f"Error getting price data for {symbol}: {error}")
                continue
                
            # Process the results
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
                logger.error(f"Error getting price data for {symbol}: Missing 'historical' data")
        
        return result
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, lambda self, symbol, annual=True, force_refresh=False: f"FinancialModelingPrepProvider.get_income_statement:{symbol}:{annual}:{force_refresh}"
    ))
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
        
        # Set up parameters
        period = "annual" if annual else "quarter"
        limit = 5 if annual else config.ScreeningThresholds.QUARTERS_RETURNED
        params = {"period": period, "limit": limit}
        
        # Make API request
        success, data, error = self._make_api_request(
            endpoint="income-statement",
            symbol=symbol,
            params=params
        )
        
        if not success:
            logger.error(f"Error getting income statement for {symbol}: {error}")
            return pd.DataFrame()
        
        # Column mapping for income statement
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
        
        # Process the data
        return self._process_financial_statement(data, column_mapping)
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, lambda self, symbol, annual=True, force_refresh=False: f"FinancialModelingPrepProvider.get_balance_sheet:{symbol}:{annual}:{force_refresh}"
    ))
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
        
        # Set up parameters
        period = "annual" if annual else "quarter"
        limit = 5 if annual else config.ScreeningThresholds.QUARTERS_RETURNED
        params = {"period": period, "limit": limit}
        
        # Make API request
        success, data, error = self._make_api_request(
            endpoint="balance-sheet-statement",
            symbol=symbol,
            params=params
        )
    
        if not success:
            logger.error(f"Error getting balance sheet for {symbol}: {error}")
            return pd.DataFrame()
        
        # Column mapping for balance sheet
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
        
        # Process the data
        return self._process_financial_statement(data, column_mapping)
    @cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, lambda self, symbol, annual=True, force_refresh=False: f"FinancialModelingPrepProvider.get_cash_flow:{symbol}:{annual}:{force_refresh}"
    ))
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
        
        # Set up parameters
        period = "annual" if annual else "quarter"
        limit = 5 if annual else config.ScreeningThresholds.QUARTERS_RETURNED
        params = {"period": period, "limit": limit}
        
        # Make API request
        success, data, error = self._make_api_request(
            endpoint="cash-flow-statement",
            symbol=symbol,
            params=params
        )
        
        if not success:
            logger.error(f"Error getting cash flow for {symbol}: {error}")
            return pd.DataFrame()
        
        # Column mapping for cash flow
        column_mapping = {
            "netCashProvidedByOperatingActivities": "operatingCashflow",
            "capitalExpenditure": "capitalExpenditures",
            "freeCashFlow": "freeCashflow",
            "dividendsPaid": "dividendPayout",
            "netChangeInCash": "changeInCash",
            "stockRepurchased": "repurchaseOfStock",
            "commonStockIssued": "issuanceOfStock"
        }
        
        # Process the data
        return self._process_financial_statement(data, column_mapping)
        
    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, lambda self, symbol, force_refresh=False: f"FinancialModelingPrepProvider.get_company_overview:{symbol}:{force_refresh}"
    ))
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data from Financial Modeling Prep API.
        
        This method aggregates data from multiple FMP endpoints to ensure
        all required metrics are available:
        - /profile/{symbol} - Basic company information and some metrics
        - /quote/{symbol} - Latest market data including price, 52-week high/low
        - /key-metrics/{symbol} - Additional financial metrics
        - /market-capitalization/{symbol} - Specific market cap information
        - /ratios/{symbol} - Financial ratios including P/E, P/B, P/S
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company profile and metrics
        """
        if force_refresh:
            cache.delete(self.get_company_overview, symbol)
        
        # Initialize the overview dictionary
        overview = {
            'Symbol': symbol,
            'DataCompleteness': 'partial',
        }
        
        # Step 1: Get profile data (basic company info)
        success, profile_data, _ = self._make_api_request("profile", symbol)
        if not success or not profile_data:
            logger.error(f"Could not get profile data for {symbol}")
            return {}
        
        # Process profile data
        profile = profile_data[0]
        overview['Name'] = profile.get('companyName', '')
        overview['Description'] = profile.get('description', '')
        overview['Exchange'] = profile.get('exchange', '')
        overview['Sector'] = profile.get('sector', '')
        overview['Industry'] = profile.get('industry', '')
        overview['MarketCapitalization'] = profile.get('mktCap', '')
        overview['Beta'] = profile.get('beta', '')
        
        # Extract 52-week high/low from range if available
        if '-' in profile.get('range', ''):
            range_parts = profile.get('range', '').split('-')
            if len(range_parts) == 2:
                overview['52WeekLow'] = range_parts[0].strip()
                overview['52WeekHigh'] = range_parts[1].strip()
        
        overview['LastDividendDate'] = profile.get('lastDiv', '')
        overview['SharesOutstanding'] = profile.get('sharesOutstanding', '')
        
        # Step 2: Get quote data
        success, quote_data, _ = self._make_api_request("quote", symbol)
        if success and quote_data:
            quote = quote_data[0]
            overview['MarketCapitalization'] = quote.get('marketCap', overview.get('MarketCapitalization', ''))
            overview['PERatio'] = quote.get('pe', '')
            overview['EPS'] = quote.get('eps', '')
            overview['52WeekHigh'] = quote.get('yearHigh', overview.get('52WeekHigh', ''))
            overview['52WeekLow'] = quote.get('yearLow', overview.get('52WeekLow', ''))
            overview['DataCompleteness'] = 'good'
        
        # Step 3: Get key metrics
        success, metrics_data, _ = self._make_api_request(
            "key-metrics", 
            symbol, 
            params={"period": "annual"}
        )
        
        if success and metrics_data:
            metrics = metrics_data[0]
            overview['PriceToBookRatio'] = metrics.get('priceToBookRatio', '')
            overview['PriceToSalesRatio'] = metrics.get('priceToSalesRatio', '')
            
            if overview.get('DataCompleteness') == 'good':
                overview['DataCompleteness'] = 'excellent'
        
        # Step 4: Try ratios endpoint for missing data
        if not overview.get('PriceToBookRatio') or not overview.get('PriceToSalesRatio') or not overview.get('PERatio'):
            success, ratios_data, _ = self._make_api_request(
                "ratios", 
                symbol, 
                params={"period": "annual"}
            )
            
            if success and ratios_data:
                ratio = ratios_data[0]
                
                # Fill in missing ratios
                if not overview.get('PERatio'):
                    overview['PERatio'] = ratio.get('priceEarningsRatio', '')
                    
                if not overview.get('PriceToBookRatio'):
                    overview['PriceToBookRatio'] = ratio.get('priceToBookRatio', '')
                    
                if not overview.get('PriceToSalesRatio'):
                    overview['PriceToSalesRatio'] = ratio.get('priceToSalesRatio', '')
                
                # Add additional useful ratios
                overview['ReturnOnEquityTTM'] = ratio.get('returnOnEquity', '')
                overview['ReturnOnAssetsTTM'] = ratio.get('returnOnAssets', '')
                overview['ProfitMargin'] = ratio.get('netProfitMargin', '')
                overview['OperatingMarginTTM'] = ratio.get('operatingProfitMargin', '')
                overview['DebtToEquityRatio'] = ratio.get('debtToEquity', '')
                overview['EVToEBITDA'] = ratio.get('enterpriseValueMultiple', '')
        
        # Step 5: For very accurate market cap, try the dedicated endpoint
        if not overview.get('MarketCapitalization'):
            success, market_cap_data, _ = self._make_api_request("market-capitalization", symbol)
            if success and market_cap_data:
                market_cap_entry = market_cap_data[0]
                overview['MarketCapitalization'] = market_cap_entry.get('marketCap', '')
        
        return overview

    @cache.memoize(expire=4*3600)  # Cache for 4 hours (insider data changes more frequently)
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, lambda self, symbol, lookback_days=60, force_refresh=False: f"FinancialModelingPrepProvider.get_insider_trading:{symbol}:{lookback_days}:{force_refresh}"
    ))
    def get_insider_trading(self, symbol: str, lookback_days: int = 60, force_refresh: bool = False) -> List[dict]:
        """
        Get insider trading data for a specific symbol using the stable API.
        
        Args:
            symbol: Stock symbol to get insider trading data for
            lookback_days: Number of days to look back for trades
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            List of insider trading records within the lookback period
        """
        if force_refresh:
            # Clear cache for this specific call
            cache_key = f"FinancialModelingPrepProvider.get_insider_trading:{symbol}:{lookback_days}:{force_refresh}"
            try:
                cache.delete(cache_key)
            except:
                pass  # Ignore cache deletion errors
            
        from datetime import datetime, timedelta
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Apply rate limiting
            fmp_rate_limiter.wait_if_needed()
            
            # Use symbol-specific API endpoint for comprehensive coverage
            url = f"https://financialmodelingprep.com/stable/insider-trading/search"
            params = {
                'symbol': symbol,
                'page': 0,
                'limit': 100,
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error fetching insider trading data for {symbol}: {response.status_code}")
                return []
                
            data = response.json()
            if not data:
                return []
            
            # Filter by date - only return trades within lookback period
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            recent_trades = []
            
            for trade in data:
                try:
                    trade_date = datetime.strptime(trade['transactionDate'], '%Y-%m-%d')
                    if trade_date >= cutoff_date:
                        recent_trades.append(trade)
                except (KeyError, ValueError):
                    # Skip trades with invalid or missing dates
                    continue
            
            logger.debug(f"Retrieved {len(recent_trades)} insider trades for {symbol} (last {lookback_days} days)")
            return recent_trades
            
        except Exception as e:
            logger.error(f"Error fetching insider trading data for {symbol}: {e}")
            return []
