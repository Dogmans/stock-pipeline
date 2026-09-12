"""
Financial Modeling Prep data provider for retrieving financial data.

This module implements the BaseDataProvider interface for Financial Modeling Prep API.

⚠️ IMPORTANT: See data_providers/fmp_types.py for complete field documentation

Common Field Names (see fmp_types.py for full reference):
- Income Statement: Use 'totalRevenue' NOT 'revenue'
- Balance Sheet: Use 'totalEquity' or 'totalShareholderEquity' NOT 'totalStockholdersEquity'
- Price History: Use 'Close', 'High', 'Low' (capitalized) NOT 'close', 'high', 'low'
- Overview: ReturnOnEquityTTM is DECIMAL (0.30 = 30%), NOT percentage
- Current Ratio: NOT in overview, calculate from balance sheet

For detailed type definitions and examples, see: data_providers.fmp_types
"""
from typing import Dict, List, Union, Any
from datetime import datetime, timezone
import pandas as pd
import requests
import atexit
import functools
from tqdm import tqdm  # For progress bars

from .base import BaseDataProvider
from .fmp_types import (
    FMPCompanyOverview,
    FMPIncomeStatement,
    FMPBalanceSheet,
    FMPCashFlow,
    FMPHistoricalPrice,
    FMPPriceTarget,
    FMPAnalystGrades
)
from cache_config import cache, clear_all_cache
import config
from utils.logger import get_logger
from utils.rate_limiter import RateLimiter
from utils.throttling import throttler, create_cache_checker

# Get logger for this module
logger = get_logger(__name__)

# Get rate limiter instance for Financial Modeling Prep
fmp_rate_limiter = RateLimiter.get_instance("financial_modeling_prep")

# Share the connection pool across screeners without adding mutable transport state
# to provider instances, which DiskCache serializes as part of memoization keys.
fmp_http_session = requests.Session()
atexit.register(fmp_http_session.close)

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
        
        # Base URL for FMP API (legacy and stable endpoints)
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.stable_base_url = "https://financialmodelingprep.com/stable"
        self.query_string_endpoints = {
            "historical-price-eod/full",
            "grades",
            "grades-consensus",
            "grades-historical",
            "price-target-summary",
            "price-target-consensus",
            "analyst-estimates"
        }
    
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
        # Initialize params dictionary if None
        if params is None:
            params = {}

        # Determine the URL format for this endpoint
        if endpoint in self.query_string_endpoints:
            # Stable endpoints use query-string symbol parameters
            params["symbol"] = symbol
            url = f"{self.stable_base_url}/{endpoint}"
        else:
            url = f"{self.base_url}/{endpoint}/{symbol}"
        
        # Always include API key
        params["apikey"] = self.api_key
        
        try:
            # Apply legacy rate limiting if requested (cache-aware throttling is handled by decorators)
            if rate_limit:
                fmp_rate_limiter.wait_if_needed()
                
            # Make the request
            response = fmp_http_session.get(url, params=params, timeout=(5, 20))
            
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
    
    @cache.memoize(expire=24*3600)
    def get_price_change_history(self, symbol, from_date, to_date):
        """Daily split-adjusted closes from FMP's stable EOD endpoint.

        Kept separate from legacy price consumers; no dividend adjustment is applied.
        https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full
        """
        success, data, error = self._make_api_request('historical-price-eod/full', symbol,
                                                     {'from':from_date, 'to':to_date})
        if not success or not isinstance(data,list):
            # Do not cache transient failures as an empty history.
            raise RuntimeError('FMP daily price history is unavailable.')
        return pd.DataFrame(data).rename(columns={'date':'Date','close':'Close'})

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
        cache, "get_historical_prices"
    ))
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data using Financial Modeling Prep API.
        
        Returns dict of DataFrames with FMPHistoricalPrice rows.
        See data_providers.fmp_types.FMPHistoricalPrice for complete field list.
        
        ⚠️ CRITICAL: Column names are CAPITALIZED
        - Use 'Close' NOT 'close'
        - Use 'High' NOT 'high'
        - Use 'Low' NOT 'low'
        - Use 'Open' NOT 'open'
        - Use 'Volume' NOT 'volume'
        
        Args:
            symbols: Single symbol or list of stock symbols
            period: Time period to retrieve (e.g., '1y', '6m', '1d')
            interval: Data interval (e.g., '1d', '1h', '5m')
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary mapping each symbol to its historical price DataFrame
            Each DataFrame has columns: Date, Open, High, Low, Close, Volume
        """
        # Global cache clearing when force_refresh=True
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
            
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
        cache, "get_income_statement"
    ))
    def get_income_statement(self, symbol: str, 
                            annual: bool = True,
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        Get income statement data from Financial Modeling Prep API.
        
        Returns DataFrame with FMPIncomeStatement rows.
        See data_providers.fmp_types.FMPIncomeStatement for complete field list.
        
        ⚠️ Key Field Names:
        - Use 'totalRevenue' NOT 'revenue'
        - 'operatingIncome', 'netIncome', 'costOfRevenue' are correct
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame where each row is an FMPIncomeStatement
        """
        # Global cache clearing when force_refresh=True
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
        
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
        cache, "get_balance_sheet"
    ))
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data from Financial Modeling Prep API.
        
        Returns DataFrame with FMPBalanceSheet rows.
        See data_providers.fmp_types.FMPBalanceSheet for complete field list.
        
        ⚠️ Key Field Names:
        - Use 'totalEquity' or 'totalShareholderEquity' NOT 'totalStockholdersEquity'
        - 'totalCurrentAssets' and 'totalCurrentLiabilities' for current ratio
        - 'totalDebt', 'cash' are correct
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame where each row is an FMPBalanceSheet
        """
        # Global cache clearing when force_refresh=True
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
        
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
        cache, "get_cash_flow"
    ))
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data from Financial Modeling Prep API.
        
        Returns DataFrame with FMPCashFlow rows.
        See data_providers.fmp_types.FMPCashFlow for complete field list.
        
        ⚠️ Key Field Names:
        - Free cash flow may be 'freeCashflow' OR 'freeCashFlow' - check both!
        - 'operatingCashflow', 'capitalExpenditures' are correct
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame where each row is an FMPCashFlow
        """
        # Global cache clearing when force_refresh=True
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
        
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
        cache, "get_company_overview"
    ))
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> FMPCompanyOverview:
        """
        Get company overview data from Financial Modeling Prep API.
        
        Returns FMPCompanyOverview with all available fields.
        See data_providers.fmp_types.FMPCompanyOverview for complete field list.
        
        ⚠️ Key Fields:
        - Sector, Name, Industry: Basic info
        - PERatio, PriceToBookRatio, EVToEBITDA: Valuation
        - ReturnOnEquityTTM: In DECIMAL format (0.30 = 30%)
        - CurrentRatio: NOT available, calculate from balance sheet
        
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
            FMPCompanyOverview dictionary with company profile and metrics
        """
        # Global cache clearing when force_refresh=True
        if force_refresh:
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
        
        # Initialize the overview dictionary
        overview = {
            'Symbol': symbol,
            'DataCompleteness': 'partial',
            'OverviewFetchedAt': datetime.now(timezone.utc).isoformat(),
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
        overview['ExchangeShortName'] = profile.get('exchangeShortName', '')
        overview['Currency'] = profile.get('currency', '')
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
            overview['Price'] = quote.get('price', '')
            overview['Change'] = quote.get('change', '')
            overview['ChangesPercentage'] = quote.get('changesPercentage', '')
            overview['Volume'] = quote.get('volume', '')
            overview['AverageVolume'] = quote.get('avgVolume', '')
            overview['QuoteTimestamp'] = quote.get('timestamp')
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
            overview['FinancialPeriod'] = metrics.get('date')
            overview['FreeCashFlowYield'] = metrics.get('freeCashFlowYield')
            overview['DebtToEquityRatio'] = metrics.get('debtToEquity')
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
                overview['RatiosPeriod'] = ratio.get('date')
                
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

    @cache.memoize(expire=30*60)
    @throttler.throttle(cache_check_func=create_cache_checker(cache, "get_stock_news"))
    def get_stock_news(self, symbol: str, limit: int = 8) -> list:
        """Return recent FMP news for one symbol, cached for 30 minutes."""
        params = {'symbols': symbol, 'limit': max(1, min(int(limit), 25)), 'apikey': self.api_key}
        try:
            fmp_rate_limiter.wait_if_needed()
            response = fmp_http_session.get(
                f"{self.stable_base_url}/news/stock", params=params, timeout=(5, 20)
            )
            if response.status_code != 200:
                logger.warning("Stock news unavailable for %s: HTTP %s", symbol, response.status_code)
                return []
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("Stock news unavailable for %s: %s", symbol, exc)
            return []

    @cache.memoize(expire=24*3600)  # Cache for 24 hours
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, "get_etf_holdings"
    ))
    def get_etf_holdings(self, etf_ticker: str, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get holdings for a given ETF ticker using the FMP 'etf-holder' endpoint.

        Returns a DataFrame with at least `symbol` and `security` columns and an
        optional `weight` column when present in the response.
        """
        try:
            if force_refresh:
                clear_all_cache()

            success, data, error = self._make_api_request("etf-holder", etf_ticker)
            if not success or not data:
                logger.error(f"Failed to fetch ETF holdings for {etf_ticker}: {error}")
                return pd.DataFrame()

            # Data is typically a list of holdings
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                logger.error(f"Unexpected ETF holdings format for {etf_ticker}")
                return pd.DataFrame()

            # Determine symbol and name columns in a tolerant way
            possible_symbol_cols = ['ticker', 'symbol', 'asset']
            possible_name_cols = ['name', 'security']

            symbol_col = next((c for c in possible_symbol_cols if c in df.columns), None)
            name_col = next((c for c in possible_name_cols if c in df.columns), None)

            if symbol_col:
                df['symbol'] = df[symbol_col].astype(str)
            else:
                df['symbol'] = ''

            if name_col:
                df['security'] = df[name_col]
            else:
                df['security'] = ''

            # Normalize weight if available
            if 'weight' in df.columns:
                df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
            else:
                df['weight'] = None

            # Keep only relevant columns and drop invalid entries
            df = df[['symbol', 'security', 'weight']]
            df = df.dropna(subset=['symbol'])
            df = df[df['symbol'].astype(str).str.strip() != '']
            df = df.drop_duplicates(subset=['symbol'])
            df = df.reset_index(drop=True)

            return df
        except Exception as e:
            logger.error(f"Exception fetching ETF holdings for {etf_ticker}: {e}")
            return pd.DataFrame()

    @cache.memoize(expire=4*3600)  # Cache for 4 hours (insider data changes more frequently)
    @throttler.throttle(cache_check_func=create_cache_checker(
        cache, "get_insider_trading"
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
        from datetime import datetime, timedelta
        import logging
        
        logger = logging.getLogger(__name__)
        
        if force_refresh:
            # Global cache clearing when force_refresh=True
            logger.info("Force refresh requested - clearing all cache")
            clear_all_cache()
        
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
            
            response = fmp_http_session.get(url, params=params, timeout=15)
            
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

    def get_analyst_estimates(self, symbol: str, period: str = "annual", force_refresh: bool = False) -> pd.DataFrame:
        """
        Get analyst financial estimates for a symbol.
        
        Args:
            symbol: Stock symbol
            period: "annual" or "quarterly" 
            force_refresh: Force refresh cache
            
        Returns:
            DataFrame with analyst estimates data
        """
        try:
            params = {"period": period}
            
            success, data, error = self._make_api_request("analyst-estimates", symbol, params)
            if not success:
                logger.error(f"Error fetching analyst estimates for {symbol}: {error}")
                return pd.DataFrame()
                
            if data:
                df = pd.DataFrame(data)
                if not df.empty:
                    df['symbol'] = symbol
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching analyst estimates for {symbol}: {e}")
            return pd.DataFrame()

    def get_analyst_grades(self, symbol: str, limit: int = 100, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get recent analyst rating changes (upgrades/downgrades).
        
        Args:
            symbol: Stock symbol
            limit: Number of recent ratings to retrieve
            force_refresh: Force refresh cache
            
        Returns:
            DataFrame with rating changes
        """
        try:
            params = {"limit": limit}
            
            success, data, error = self._make_api_request("grades", symbol, params)
            if not success:
                logger.error(f"Error fetching analyst grades for {symbol}: {error}")
                return pd.DataFrame()
                
            if data:
                df = pd.DataFrame(data)
                if not df.empty:
                    df['symbol'] = symbol
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching analyst grades for {symbol}: {e}")
            return pd.DataFrame()

    def get_analyst_grades_consensus(self, symbol: str, force_refresh: bool = False) -> dict:
        """
        Get current consensus analyst ratings summary.
        
        Args:
            symbol: Stock symbol
            force_refresh: Force refresh cache
            
        Returns:
            Dictionary with consensus ratings data
        """
        try:
            params = {}
            
            success, data, error = self._make_api_request("grades-consensus", symbol, params)
            if not success:
                logger.error(f"Error fetching analyst consensus for {symbol}: {error}")
                return {}
                
            if data and len(data) > 0:
                consensus_data = data[0] if isinstance(data, list) else data
                consensus_data['symbol'] = symbol
                return consensus_data
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching analyst consensus for {symbol}: {e}")
            return {}

    def get_analyst_upgrades_downgrades(self, symbol: str, force_refresh: bool = False) -> list:
        """
        Get analyst upgrades and downgrades for a symbol.
        Note: This endpoint appears to be empty, so we return empty list.
        
        Args:
            symbol: Stock symbol
            force_refresh: Force refresh cache
            
        Returns:
            List of upgrade/downgrade records (currently empty)
        """
        try:
            params = {}
            
            success, data, error = self._make_api_request("upgrades-downgrades", symbol, params)
            if success and data:
                return data
            else:
                logger.warning(f"No upgrades/downgrades data for {symbol}: {error}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching upgrades/downgrades for {symbol}: {e}")
            return []

    def get_price_target_summary(self, symbol: str, force_refresh: bool = False) -> dict:
        """
        Get price target summary across time periods.
        
        Args:
            symbol: Stock symbol
            force_refresh: Force refresh cache
            
        Returns:
            Dictionary with price target summary
        """
        try:
            params = {}
            
            success, data, error = self._make_api_request("price-target-summary", symbol, params)
            if not success:
                logger.error(f"Error fetching price target summary for {symbol}: {error}")
                return {}
                
            if data and len(data) > 0:
                target_data = data[0] if isinstance(data, list) else data
                target_data['symbol'] = symbol
                return target_data
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching price target summary for {symbol}: {e}")
            return {}

    def get_price_target_consensus(self, symbol: str, force_refresh: bool = False) -> dict:
        """
        Get current consensus price targets.
        
        Args:
            symbol: Stock symbol  
            force_refresh: Force refresh cache
            
        Returns:
            Dictionary with consensus price targets
        """
        try:
            params = {}
            
            success, data, error = self._make_api_request("price-target-consensus", symbol, params)
            if not success:
                logger.error(f"Error fetching price target consensus for {symbol}: {error}")
                return {}
                
            if data and len(data) > 0:
                consensus_data = data[0] if isinstance(data, list) else data
                consensus_data['symbol'] = symbol
                return consensus_data
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching price target consensus for {symbol}: {e}")
            return {}

    def get_analyst_grades_historical(self, symbol: str, limit: int = 100, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get historical analyst rating counts over time.
        
        Args:
            symbol: Stock symbol
            limit: Number of historical records
            force_refresh: Force refresh cache
            
        Returns:
            DataFrame with historical rating counts
        """
        try:
            params = {"limit": limit}
            
            success, data, error = self._make_api_request("grades-historical", symbol, params)
            if not success:
                logger.error(f"Error fetching historical analyst ratings for {symbol}: {error}")
                return pd.DataFrame()
                
            if data:
                df = pd.DataFrame(data)
                if not df.empty:
                    df['symbol'] = symbol
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching historical analyst ratings for {symbol}: {e}")
            return pd.DataFrame()
