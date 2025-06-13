"""
universe.py - Stock universe selection functions with caching.

This module provides functions for defining and retrieving various 
stock universes (e.g., S&P 500, NASDAQ 100, Russell 2000) which serve 
as the basis for stock screening. All functions use caching to minimize 
redundant network requests.

Functions:
    get_sp500_symbols(): Get cached list of S&P 500 companies
    get_russell2000_symbols(): Get cached list of Russell 2000 companies
    get_nasdaq100_symbols(): Get cached list of NASDAQ 100 companies
    get_stock_universe(): Get the specified universe of stocks with caching
"""

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import finnhub

import config
from utils import setup_logging
from cache_manager import cache_api_call

# Set up logger for this module
logger = setup_logging()

@cache_api_call(expiry_hours=24, cache_key_prefix="sp500_symbols")
def get_sp500_symbols():
    """
    Get a list of S&P 500 tickers from Wikipedia.
    
    Scrapes the current S&P 500 component list from Wikipedia and returns
    a DataFrame with symbols, company names, and sector classifications.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
        
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        tables = pd.read_html(url)
        df = tables[0]
        df.columns = [col.replace(' ', '_').lower() for col in df.columns]
        
        # Clean up the symbols
        df['symbol'] = df['symbol'].str.replace('.', '-')
        
        # Select relevant columns
        result = df[['symbol', 'security', 'gics_sector', 'gics_sub-industry']]
        logger.info(f"Successfully retrieved {len(result)} S&P 500 symbols")
        return result
    except Exception as e:
        logger.error(f"Error fetching S&P 500 symbols: {e}")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache_api_call(expiry_hours=24, cache_key_prefix="russell2000_symbols")
def get_russell2000_symbols():
    """
    Get a list of Russell 2000 tickers.
    
    Attempts to load symbols from cache first. If not available,
    tries to fetch from Finnhub API if an API key is provided.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
                  (note that for Russell 2000, sector info may be empty)
    """
    # Try to load from cached file first
    russell_file = os.path.join(config.DATA_DIR, 'russell2000.csv')
    
    if os.path.exists(russell_file):
        try:
            df = pd.read_csv(russell_file)
            logger.info(f"Loaded {len(df)} Russell 2000 symbols from cache")
            return df
        except Exception as e:
            logger.error(f"Error loading Russell 2000 symbols from cache: {e}")
    
    # If we can't load from cache, use a finnhub API if available
    if config.FINNHUB_API_KEY:
        try:
            finnhub_client = finnhub.Client(api_key=config.FINNHUB_API_KEY)
            russell_stocks = finnhub_client.indices_const(symbol="^RUT")
            if russell_stocks and 'constituents' in russell_stocks:
                symbols = russell_stocks['constituents']
                df = pd.DataFrame(symbols, columns=['symbol'])
                
                # Add placeholders for other columns to match S&P 500 format
                df['security'] = ''
                df['gics_sector'] = ''
                df['gics_sub-industry'] = ''
                
                # Cache the results
                df.to_csv(russell_file, index=False)
                logger.info(f"Fetched and saved {len(df)} Russell 2000 symbols")
                return df
        except Exception as e:
            logger.error(f"Error fetching Russell 2000 symbols from Finnhub: {e}")
    
    logger.warning("Could not fetch Russell 2000 symbols. Returning empty DataFrame.")
    return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache_api_call(expiry_hours=24, cache_key_prefix="nasdaq100_symbols")
def get_nasdaq100_symbols():
    """
    Get a list of NASDAQ 100 tickers from Wikipedia.
    
    Scrapes the current NASDAQ 100 component list from Wikipedia and returns
    a DataFrame with symbols and company names.
    
    Args:
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company information
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
                  (note that sector info may be empty)
    """
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
            logger.info(f"Successfully retrieved {len(result)} NASDAQ 100 symbols")
            return result
        
        logger.error("Could not find appropriate table for NASDAQ 100 components")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])
    except Exception as e:
        logger.error(f"Error fetching NASDAQ 100 symbols: {e}")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

@cache_api_call(expiry_hours=24, cache_key_prefix="stock_universe")
def get_stock_universe(universe=None, force_refresh=False):
    """
    Get a list of stock symbols based on the specified universe.
    Results are cached for 24 hours by default.
    
    Args:
        universe (str): Which universe of stocks to use. Options:
                        'sp500', 'russell2000', 'nasdaq100', 'all'
                        If None, uses the default universe from config
        force_refresh (bool): If True, bypass cache and fetch fresh data
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with ticker symbols and metadata
                  Columns: 'symbol', 'security', 'gics_sector', 'gics_sub-industry'
    """
    if universe is None:
        universe = config.DEFAULT_UNIVERSE
    
    if universe == config.UNIVERSES["SP500"]:
        return get_sp500_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["RUSSELL2000"]:
        return get_russell2000_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["NASDAQ100"]:
        return get_nasdaq100_symbols(force_refresh=force_refresh)
    elif universe == config.UNIVERSES["ALL"]:
        # Combine all universes
        sp500 = get_sp500_symbols(force_refresh=force_refresh)
        russell = get_russell2000_symbols(force_refresh=force_refresh)
        nasdaq = get_nasdaq100_symbols(force_refresh=force_refresh)
        
        # Combine and remove duplicates
        combined = pd.concat([sp500, russell, nasdaq])
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
    
    # Test NASDAQ 100 retrieval
    nasdaq = get_nasdaq100_symbols()
    logger.info(f"NASDAQ 100: Retrieved {len(nasdaq)} symbols")
    if not nasdaq.empty:
        logger.info(f"Sample NASDAQ 100 symbols: {', '.join(nasdaq['symbol'].head(5).tolist())}")
    
    # Test Russell 2000 retrieval
    russell = get_russell2000_symbols()
    logger.info(f"Russell 2000: Retrieved {len(russell)} symbols")
    if not russell.empty:
        logger.info(f"Sample Russell 2000 symbols: {', '.join(russell['symbol'].head(5).tolist())}")
    
    # Test combined universe
    all_stocks = get_stock_universe("all")
    logger.info(f"Combined universe contains {len(all_stocks)} unique symbols")
    
    logger.info("Universe module test complete")
