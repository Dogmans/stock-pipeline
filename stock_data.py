"""
stock_data.py - Individual stock data collection functions.

This module provides functions for retrieving historical price data and
fundamental information for individual stocks.

Functions:
    get_historical_prices(): Fetch historical price data for multiple stocks
    get_fundamental_data(): Fetch fundamental data for multiple stocks
    fetch_52_week_lows(): Find stocks near their 52-week lows
"""

import pandas as pd
import numpy as np
import yfinance as yf
import time
from tqdm import tqdm
from alpha_vantage.fundamentaldata import FundamentalData

import config
from utils.logger import setup_logging
from universe import get_stock_universe
from cache_manager import cache_api_call
import data_providers
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider

# Set up logger for this module
logger = setup_logging()

# Default data provider - Financial Modeling Prep since we have a paid subscription
default_provider = FinancialModelingPrepProvider()

@cache_api_call(cache_key_prefix="historical_prices")
def get_historical_prices(symbols, period="1y", interval="1d", force_refresh=False, provider=None):
    """
    Fetch historical price data for a list of symbols.
    
    Retrieves OHLCV (Open, High, Low, Close, Volume) data for the specified
    symbols, with batching to handle API rate limits.
    
    Args:
        symbols (list): List of ticker symbols
        period (str): Time period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
        provider (BaseDataProvider, optional): Data provider to use. If None, uses Financial Modeling Prep.
    
    Returns:
        dict: Dictionary of DataFrames with historical price data,
              keyed by symbol
    """
    # Use the specified provider or the default Financial Modeling Prep provider
    data_provider = provider or default_provider
    
    # Use the provider to get historical prices
    return data_provider.get_historical_prices(symbols, period, interval, force_refresh)
    
    # Legacy implementation below for reference
    """
    price_data = {}
    
    # Handle case where symbols is a single string
    if isinstance(symbols, str):
        symbols = [symbols]
    """
    
    # Use a batch approach with tqdm progress bar
    chunk_size = 50  # Process in batches to avoid rate limiting
    for i in tqdm(range(0, len(symbols), chunk_size), desc="Fetching historical prices"):
        chunk = symbols[i:i+chunk_size]
        
        try:
            # Fetch data for the chunk of symbols
            data = yf.download(chunk, period=period, interval=interval, group_by="ticker", progress=False)
            
            # If only one symbol is requested, the structure is different
            if len(chunk) == 1:
                symbol = chunk[0]
                price_data[symbol] = data
            else:
                # Extract data for each symbol
                for symbol in chunk:
                    try:
                        # Skip if the symbol wasn't found
                        if (symbol,) not in data.columns.levels[0]:
                            continue
                        
                        # Get data for this symbol
                        symbol_data = data[symbol].copy()
                        price_data[symbol] = symbol_data
                    except Exception as e:
                        logger.error(f"Error processing data for {symbol}: {e}")
            
            # Sleep to avoid hitting API limits
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error downloading batch data: {e}")
    
    logger.info(f"Successfully retrieved historical prices for {len(price_data)} symbols")
    return price_data

@cache_api_call(expiry_hours=24, cache_key_prefix="fundamental_data")
def get_fundamental_data(symbols, force_refresh=False, provider=None):
    """
    Fetch fundamental data for a list of symbols using the Financial Modeling Prep provider.
    
    Retrieves income statements, balance sheets, cash flow statements,
    and company overviews.
    
    Args:
        symbols (list): List of ticker symbols
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
        provider (BaseDataProvider, optional): Data provider to use. If None, uses Financial Modeling Prep.
    
    Returns:
        dict: Dictionary with fundamental data for each symbol
    """
    # Use the specified provider or the default Financial Modeling Prep provider
    data_provider = provider or default_provider
    
    # Handle case where symbols is a single string
    if isinstance(symbols, str):
        symbols = [symbols]
      # Check if we should process in small batches to respect API limits
    batch_size = 10  # Small batch size to avoid hitting API limits
    fundamental_data = {}
    
    if len(symbols) <= batch_size:
        # Process all at once if small enough
        return data_provider.get_batch_fundamental_data(symbols, force_refresh=force_refresh)
    else:
        # Process in batches to respect API limits
        chunks = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]
        
        for i, chunk in enumerate(tqdm(chunks, desc="Fetching fundamental data")):
            try:
                chunk_data = data_provider.get_batch_fundamental_data(
                    chunk, 
                    force_refresh=force_refresh,
                    max_workers=5,
                    rate_limit=getattr(data_provider, 'RATE_LIMIT', None)
                )
                fundamental_data.update(chunk_data)
                
                # Log progress
                logger.info(f"Processed batch {i+1}/{len(chunks)} ({len(chunk)} symbols)")
                
            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {e}")
    
    logger.info(f"Successfully retrieved fundamental data for {len(fundamental_data)} symbols")
    return fundamental_data

@cache_api_call(expiry_hours=24, cache_key_prefix="52_week_lows")
def fetch_52_week_lows(top_n=50, force_refresh=False, provider=None):
    """
    Fetch stocks currently at or near their 52-week lows.
    
    Identifies stocks trading close to their 52-week lows,
    which can be potential value opportunities.
    
    Args:
        top_n (int): Number of stocks to return
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
        provider (BaseDataProvider, optional): Data provider to use. If None, uses Financial Modeling Prep.
    
    Returns:
        DataFrame: DataFrame with stocks at or near 52-week lows, sorted by
                  percentage above 52-week low (ascending)
    """
    universe = get_stock_universe()
    symbols = universe['symbol'].tolist()
    
    # Get historical data for all symbols
    hist_data = get_historical_prices(symbols, period="1y", force_refresh=force_refresh, provider=provider)
    
    results = []
    for symbol, data in hist_data.items():
        try:
            if data is None or data.empty:
                continue
            
            # Calculate 52-week low and current price
            low_52_week = data['Low'].min()
            current_price = data['Close'].iloc[-1]
            high_52_week = data['High'].max()
            
            # Calculate percentage above 52-week low
            pct_above_low = ((current_price / low_52_week) - 1) * 100
            
            # Calculate percentage below 52-week high
            pct_below_high = ((high_52_week - current_price) / high_52_week) * 100
            
            # Calculate YTD change
            start_of_year_data = data[data.index.year == data.index[0].year].iloc[0]
            start_of_year = start_of_year_data['Close']
            ytd_change = ((current_price / start_of_year) - 1) * 100
            
            # Get company name from universe
            company_name = universe.loc[universe['symbol'] == symbol, 'security'].values[0] if symbol in universe['symbol'].values else symbol
            sector = universe.loc[universe['symbol'] == symbol, 'gics_sector'].values[0] if 'gics_sector' in universe.columns and symbol in universe['symbol'].values else 'Unknown'
            
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                '52_week_low': low_52_week,
                '52_week_high': high_52_week,
                'pct_above_low': pct_above_low,
                'pct_below_high': pct_below_high,
                'ytd_change': ytd_change
            })
            
        except Exception as e:
            logger.error(f"Error processing 52-week low data for {symbol}: {e}")
    
    # Convert to DataFrame and sort
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('pct_above_low')
        logger.info(f"Found {len(df)} stocks with 52-week low data")
        return df.head(top_n)
    else:
        logger.warning("No stocks found with 52-week low data")
        return pd.DataFrame(columns=['symbol', 'company_name', 'sector', 'current_price', 
                                    '52_week_low', '52_week_high', 'pct_above_low', 
                                    'pct_below_high', 'ytd_change'])

if __name__ == "__main__":
    # Test module functionality
    logger.info("Testing stock data module...")
    
    # Test historical price retrieval for a few symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOG']
    prices = get_historical_prices(test_symbols)
    for symbol, data in prices.items():
        if not data.empty:
            logger.info(f"{symbol}: {len(data)} days of data, current price: ${data['Close'].iloc[-1]:.2f}")
    
    # Test 52-week lows function
    lows = fetch_52_week_lows(top_n=5)
    if not lows.empty:
        logger.info(f"Top 5 stocks near 52-week lows:")
        for _, row in lows.iterrows():
            logger.info(f"{row['symbol']} ({row['company_name']}): {row['pct_above_low']:.2f}% above 52-week low")
    
    # Test fundamental data if API key is available (limited to one symbol for testing)
    if config.ALPHA_VANTAGE_API_KEY:
        fundamentals = get_fundamental_data(['AAPL'])
        if fundamentals and 'AAPL' in fundamentals:
            logger.info(f"Successfully retrieved fundamental data for AAPL")
    
    logger.info("Stock data module test complete")
