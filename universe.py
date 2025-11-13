"""
universe.py - Stock universe selection functions with caching.

This module provides functions for defining and retrieving various 
stock universes (e.g., S&P 500, NASDAQ 100, Russell 2000) which serve 
as the basis for stock screening. All functions use caching to minimize 
redundant network requests.

Functions:
    get_sp500_symbols(): Get cached list of S&P 500 companies from Wikipedia
    get_russell2000_symbols(): Get cached list of Russell 2000 companies from iShares ETF holdings
    get_nasdaq100_symbols(): Get cached list of NASDAQ 100 companies
    get_stock_universe(): Get the specified universe of stocks with caching
"""

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import finnhub

import config
from utils.logger import setup_logging
from cache_config import cache

# Set up logger for this module
logger = setup_logging()

def _fetch_fmp_constituents(endpoint, index_name):
    """
    Common helper function to fetch index constituents from Financial Modeling Prep API.
    
    Args:
        endpoint (str): The FMP API endpoint (e.g., 'sp500_constituent')
        index_name (str): Human-readable name for logging (e.g., 'S&P 500')
        
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    try:
        import requests
        url = f'https://financialmodelingprep.com/api/v3/{endpoint}'
        
        response = requests.get(url, params={'apikey': config.FINANCIAL_MODELING_PREP_API_KEY})
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                # Convert to DataFrame and rename columns to match expected format
                df = pd.DataFrame(data)
                
                # Map FMP columns to expected column names
                result = pd.DataFrame({
                    'symbol': df['symbol'],
                    'security': df['name'],
                    'gics_sector': df.get('sector', ''),
                    'gics_sub-industry': df.get('subSector', df.get('sector', ''))
                })
                
                logger.info(f"Successfully retrieved {len(result)} {index_name} symbols from Financial Modeling Prep")
                return result
            else:
                logger.warning(f"Empty or invalid response from Financial Modeling Prep {index_name} API")
                return None
        else:
            logger.warning(f"Error fetching {index_name} symbols from FMP: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Error fetching {index_name} symbols from Financial Modeling Prep: {e}")
        return None

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def get_sp500_symbols(force_refresh=False):
    """
    Get a list of S&P 500 tickers from Financial Modeling Prep API.
    
    Fetches the current S&P 500 component list from FMP and returns
    a DataFrame with symbols, company names, and sector classifications.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
        
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    if force_refresh:
        cache.delete(get_sp500_symbols)
        
    result = _fetch_fmp_constituents('sp500_constituent', 'S&P 500')
    
    if result is not None:
        return result
    else:
        logger.error("Failed to fetch S&P 500 symbols from Financial Modeling Prep")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def get_russell2000_symbols(force_refresh=False):
    """
    Get a list of Russell 2000 tickers from Financial Modeling Prep API.
    
    Fetches the current Russell 2000 component list from FMP and returns
    a DataFrame with symbols, company names, and sector classifications.
    Falls back to iShares ETF holdings if FMP API is unavailable.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    if force_refresh:
        cache.delete(get_russell2000_symbols)
    
    # Try Financial Modeling Prep API first
    result = _fetch_fmp_constituents('russell2000_constituent', 'Russell 2000')
    
    if result is not None:
        return result
    
    # Fallback to iShares ETF approach
    logger.info("Falling back to iShares ETF approach for Russell 2000")
    
    # Fallback: iShares Russell 2000 ETF (IWM) holdings CSV URL
    url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
    
    try:
        # Download the CSV file directly from iShares
        import requests
        import io
        
        logger.info("Fetching Russell 2000 symbols from iShares ETF holdings (fallback)...")
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch Russell 2000 data: HTTP {response.status_code}")
        
        # Read the CSV content (skip header rows)
        df = pd.read_csv(io.StringIO(response.text), skiprows=9)
        
        logger.info(f"Successfully retrieved {len(df)} rows of Russell 2000 data")
        
        # Remove any rows after the holdings (iShares CSVs often have footer information)
        # Look for the first empty row or rows with NaN values
        first_empty_row = df[df.iloc[:,0].isna()].index
        if len(first_empty_row) > 0:
            df = df.iloc[:first_empty_row[0]]
        
        # Keep only the ticker symbol and company name
        df = df[['Ticker', 'Name']]
        
        # Rename columns to match S&P 500 format
        df = df.rename(columns={
            'Ticker': 'symbol',
            'Name': 'security'
        })
        
        # Add empty columns for sector information to match S&P 500 format
        df['gics_sector'] = ''
        df['gics_sub-industry'] = ''
        
        # Remove any NaN values or empty strings in symbol
        df = df[df['symbol'].notna() & (df['symbol'] != '')]
        
        # Remove duplicates
        df = df.drop_duplicates(subset='symbol')
        
        logger.info(f"Successfully processed {len(df)} Russell 2000 symbols from iShares fallback")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching Russell 2000 symbols: {e}")
        # Return empty DataFrame with the expected columns
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def get_nasdaq_symbols(force_refresh=False):
    """
    Get a list of NASDAQ constituents from Financial Modeling Prep API.
    
    Fetches the current NASDAQ component list from FMP and returns
    a DataFrame with symbols, company names, and sector classifications.
    Falls back to Wikipedia scraping if FMP API is unavailable.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    if force_refresh:
        cache.delete(get_nasdaq_symbols)
    
    # Try Financial Modeling Prep API first
    result = _fetch_fmp_constituents('nasdaq_constituent', 'NASDAQ')
    
    if result is not None:
        return result
    
    # Fallback to Wikipedia scraping
    logger.info("Falling back to Wikipedia scraping for NASDAQ")
        
    # Fallback: Wikipedia scraping
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    try:
        tables = pd.read_html(url)
        
        # Find the table that contains the NASDAQ-100 components
        df = None
        for table in tables:
            if 'Ticker' in table.columns and 'Company' in table.columns:
                df = table
                break
        
        if df is not None:
            df.columns = [col.replace(' ', '_').lower() for col in df.columns]
            df = df.rename(columns={'ticker': 'symbol', 'company': 'security'})
            
            # Add placeholder columns to match S&P 500 format
            if 'gics_sector' not in df.columns:
                df['gics_sector'] = ''
            if 'gics_sub-industry' not in df.columns:
                df['gics_sub-industry'] = ''
            
            result = df[['symbol', 'security', 'gics_sector', 'gics_sub-industry']]
            logger.info(f"Successfully retrieved {len(result)} NASDAQ symbols from Wikipedia fallback")
            return result
        
        logger.error("Could not find appropriate table for NASDAQ components")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])
    except Exception as e:
        logger.error(f"Error fetching NASDAQ symbols: {e}")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def get_nasdaq100_symbols(force_refresh=False):
    """
    Get a list of NASDAQ 100 tickers from Wikipedia.
    
    This function is deprecated in favor of get_nasdaq_symbols() which uses FMP API.
    Kept for backward compatibility.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    logger.warning("get_nasdaq100_symbols() is deprecated, use get_nasdaq_symbols() instead")
    return get_nasdaq_symbols(force_refresh=force_refresh)

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def get_dowjones_symbols(force_refresh=False):
    """
    Get a list of Dow Jones Industrial Average tickers from Financial Modeling Prep API.
    
    Fetches the current DJIA component list from FMP and returns
    a DataFrame with symbols, company names, and sector classifications.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    if force_refresh:
        cache.delete(get_dowjones_symbols)
    
    result = _fetch_fmp_constituents('dowjones_constituent', 'Dow Jones')
    
    if result is not None:
        return result
    else:
        logger.error("Failed to fetch Dow Jones symbols from Financial Modeling Prep")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache.memoize(expire=24*3600)  # Cache for 24 hours
def get_stock_universe(universe=None, force_refresh=False):
    """
    Get a list of stock symbols based on the specified universe.
    Results are cached for 24 hours by default.
    
    Args:
        universe (str): Which universe of stocks to use. Options:
                        'sp500', 'russell2000', 'nasdaq100', 'all'
                        If None, uses the default universe from config
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and metadata
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    if force_refresh:
        cache.delete_memoized(get_stock_universe, universe)
    if universe is None:
        universe = config.DEFAULT_UNIVERSE
    
    if universe == config.UNIVERSES["SP500"]:
        return get_sp500_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["RUSSELL2000"]:
        return get_russell2000_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["NASDAQ100"]:
        return get_nasdaq100_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["NASDAQ"]:
        return get_nasdaq_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["DOWJONES"]:
        return get_dowjones_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["ALL"]:
        # Combine all universes
        sp500 = get_sp500_symbols(force_refresh=force_refresh)
        russell = get_russell2000_symbols(force_refresh=force_refresh)
        nasdaq = get_nasdaq_symbols(force_refresh=force_refresh)
        dowjones = get_dowjones_symbols(force_refresh=force_refresh)
        
        # Combine and remove duplicates
        combined = pd.concat([sp500, russell, nasdaq, dowjones])
        combined = combined.drop_duplicates(subset=['symbol'])
        logger.info(f"Combined universe contains {len(combined)} unique symbols")
        return combined
    else:
        logger.warning(f"Unknown universe: {universe}, defaulting to S&P 500")
        return get_sp500_symbols(force_refresh=force_refresh)

if __name__ == "__main__":
    # Test module functionality
    logger.info("Testing universe module...")
    
    # Test S&P 500 retrieval
    sp500 = get_sp500_symbols()
    logger.info(f"S&P 500: Retrieved {len(sp500)} symbols")
    if not sp500.empty:
        logger.info(f"Sample S&P 500 symbols: {', '.join(sp500['symbol'].head(5).tolist())}")
    
    # Test NASDAQ retrieval
    nasdaq = get_nasdaq_symbols()
    logger.info(f"NASDAQ: Retrieved {len(nasdaq)} symbols")
    if not nasdaq.empty:
        logger.info(f"Sample NASDAQ symbols: {', '.join(nasdaq['symbol'].head(5).tolist())}")
    
    # Test Dow Jones retrieval
    dowjones = get_dowjones_symbols()
    logger.info(f"Dow Jones: Retrieved {len(dowjones)} symbols")
    if not dowjones.empty:
        logger.info(f"Sample Dow Jones symbols: {', '.join(dowjones['symbol'].head(5).tolist())}")
    
    # Test Russell 2000 retrieval
    russell = get_russell2000_symbols()
    logger.info(f"Russell 2000: Retrieved {len(russell)} symbols")
    if not russell.empty:
        logger.info(f"Sample Russell 2000 symbols: {', '.join(russell['symbol'].head(5).tolist())}")
    
    # Test combined universe
    all_stocks = get_stock_universe("all")
    logger.info(f"Combined universe contains {len(all_stocks)} unique symbols")
    
    logger.info("Universe module test complete")
