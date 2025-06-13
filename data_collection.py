"""
This module handles data collection for the stock screening pipeline.
It fetches data from various financial APIs and websites.
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from alpha_vantage.fundamentaldata import FundamentalData
import finnhub
import time
from tqdm import tqdm

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
os.makedirs(config.DATA_DIR, exist_ok=True)

def get_sp500_symbols():
    """
    Get a list of S&P 500 tickers from Wikipedia.
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company names
    """
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        tables = pd.read_html(url)
        df = tables[0]
        df.columns = [col.replace(' ', '_').lower() for col in df.columns]
        
        # Clean up the symbols
        df['symbol'] = df['symbol'].str.replace('.', '-')
        
        # Add sector information
        return df[['symbol', 'security', 'gics_sector', 'gics_sub-industry']]
    except Exception as e:
        logger.error(f"Error fetching S&P 500 symbols: {e}")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

def get_russell2000_symbols():
    """
    Get a list of Russell 2000 tickers.
    This uses a saved CSV file since there's no easy way to scrape this.
    
    Returns:
        DataFrame: DataFrame with ticker symbols
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

def get_nasdaq100_symbols():
    """
    Get a list of NASDAQ 100 tickers from Wikipedia.
    
    Returns:
        DataFrame: DataFrame with ticker symbols and company names
    """
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    try:
        tables = pd.read_html(url)
        
        # Find the table that contains the NASDAQ-100 components
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
                
            return df[['symbol', 'security', 'gics_sector', 'gics_sub-industry']]
        
        logger.error("Could not find appropriate table for NASDAQ 100 components")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])
    except Exception as e:
        logger.error(f"Error fetching NASDAQ 100 symbols: {e}")
        return pd.DataFrame(columns=['symbol', 'security', 'gics_sector', 'gics_sub-industry'])

def get_stock_universe(universe=None):
    """
    Get a list of stock symbols based on the specified universe.
    
    Args:
        universe (str): Which universe of stocks to use. Options:
                        'sp500', 'russell2000', 'nasdaq100', 'all'
    
    Returns:
        DataFrame: DataFrame with ticker symbols and metadata
    """
    if universe is None:
        universe = config.DEFAULT_UNIVERSE
    
    if universe == config.UNIVERSES["SP500"]:
        return get_sp500_symbols()
    elif universe == config.UNIVERSES["RUSSELL2000"]:
        return get_russell2000_symbols()
    elif universe == config.UNIVERSES["NASDAQ100"]:
        return get_nasdaq100_symbols()
    elif universe == config.UNIVERSES["ALL"]:
        sp500 = get_sp500_symbols()
        russell = get_russell2000_symbols()
        nasdaq = get_nasdaq100_symbols()
        
        # Combine all universes and remove duplicates
        combined = pd.concat([sp500, russell, nasdaq])
        combined = combined.drop_duplicates(subset=['symbol'])
        return combined
    else:
        logger.warning(f"Unknown universe: {universe}, defaulting to S&P 500")
        return get_sp500_symbols()

def get_historical_prices(symbols, period="1y", interval="1d"):
    """
    Fetch historical price data for a list of symbols.
    
    Args:
        symbols (list): List of ticker symbols
        period (str): Time period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        dict: Dictionary of DataFrames with historical price data
    """
    price_data = {}
    
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
    
    return price_data

def get_fundamental_data(symbols):
    """
    Fetch fundamental data for a list of symbols using Alpha Vantage.
    
    Args:
        symbols (list): List of ticker symbols
    
    Returns:
        dict: Dictionary with fundamental data for each symbol
    """
    if not config.ALPHA_VANTAGE_API_KEY:
        logger.error("Alpha Vantage API key not found. Cannot fetch fundamental data.")
        return {}
    
    fd = FundamentalData(key=config.ALPHA_VANTAGE_API_KEY, output_format='pandas')
    fundamental_data = {}
    
    for symbol in tqdm(symbols, desc="Fetching fundamental data"):
        symbol_data = {}
        
        try:
            # Get income statement
            income_statement, _ = fd.get_income_statement_annual(symbol=symbol)
            symbol_data['income_statement'] = income_statement
            
            # Get balance sheet
            balance_sheet, _ = fd.get_balance_sheet_annual(symbol=symbol)
            symbol_data['balance_sheet'] = balance_sheet
            
            # Get cash flow
            cash_flow, _ = fd.get_cash_flow_annual(symbol=symbol)
            symbol_data['cash_flow'] = cash_flow
            
            # Get company overview
            overview, _ = fd.get_company_overview(symbol=symbol)
            symbol_data['overview'] = overview
            
            fundamental_data[symbol] = symbol_data
            
            # Sleep to avoid hitting API limits (Alpha Vantage has a limit of 5 calls per minute)
            time.sleep(12.5)  # 12.5 seconds * 4 calls = ~50 seconds for all 4 calls
            
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {symbol}: {e}")
    
    return fundamental_data

def get_market_conditions():
    """
    Fetch current market conditions, including index values and VIX.
    
    Returns:
        dict: Dictionary with market condition data
    """
    market_data = {}
    
    try:
        # Get data for market indexes
        indexes_data = yf.download(config.MARKET_INDEXES, period="1y", interval="1d", group_by="ticker")
        
        for index in config.MARKET_INDEXES:
            if (index,) in indexes_data.columns.levels[0]:
                market_data[index] = indexes_data[index].copy()
        
        # Get VIX data
        vix_data = yf.download("^VIX", period="1y", interval="1d")
        market_data['VIX'] = vix_data
        
        # Get sector ETF data
        sector_etfs = list(config.SECTOR_ETFS.keys())
        etf_data = yf.download(sector_etfs, period="1y", interval="1d", group_by="ticker")
        
        for etf in sector_etfs:
            if (etf,) in etf_data.columns.levels[0]:
                market_data[etf] = etf_data[etf].copy()
        
    except Exception as e:
        logger.error(f"Error fetching market conditions: {e}")
    
    return market_data

def fetch_52_week_lows(top_n=50):
    """
    Fetch stocks currently at or near their 52-week lows.
    
    Args:
        top_n (int): Number of stocks to return
    
    Returns:
        DataFrame: DataFrame with stocks at or near 52-week lows
    """
    universe = get_stock_universe()
    symbols = universe['symbol'].tolist()
    
    # Get historical data for all symbols
    hist_data = get_historical_prices(symbols, period="1y")
    
    results = []
    for symbol, data in hist_data.items():
        try:
            if data is None or data.empty:
                continue
            
            # Calculate 52-week low and current price
            low_52_week = data['Low'].min()
            current_price = data['Close'].iloc[-1]
            
            # Calculate percentage above 52-week low
            pct_above_low = ((current_price / low_52_week) - 1) * 100
            
            # Calculate YTD change
            start_of_year = data[data.index.year == data.index[0].year].iloc[0]['Close']
            ytd_change = ((current_price / start_of_year) - 1) * 100
            
            # Get company name from universe
            company_name = universe.loc[universe['symbol'] == symbol, 'security'].values[0] if symbol in universe['symbol'].values else symbol
            
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'current_price': current_price,
                '52_week_low': low_52_week,
                'pct_above_low': pct_above_low,
                'ytd_change': ytd_change
            })
            
        except Exception as e:
            logger.error(f"Error processing 52-week low data for {symbol}: {e}")
    
    # Convert to DataFrame and sort
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('pct_above_low')
        return df.head(top_n)
    else:
        return pd.DataFrame(columns=['symbol', 'company_name', 'current_price', '52_week_low', 'pct_above_low', 'ytd_change'])

def is_market_in_correction():
    """
    Determine if the market is in a correction or crash based on VIX levels.
    
    Returns:
        tuple: (bool, str) - Is in correction state and description
    """
    try:
        # Get latest VIX value
        vix_data = yf.download("^VIX", period="5d", interval="1d")
        latest_vix = vix_data['Close'].iloc[-1]
        
        if latest_vix >= config.VIX_BLACK_SWAN_THRESHOLD:
            return True, f"Black Swan Event (VIX: {latest_vix:.2f})"
        elif latest_vix >= config.VIX_CORRECTION_THRESHOLD:
            return True, f"Market Correction (VIX: {latest_vix:.2f})"
        else:
            return False, f"Normal Market Conditions (VIX: {latest_vix:.2f})"
            
    except Exception as e:
        logger.error(f"Error checking market correction status: {e}")
        return False, "Unknown (Error fetching data)"

def get_sector_performances():
    """
    Calculate the performance of different market sectors.
    
    Returns:
        DataFrame: DataFrame with sector performance data
    """
    try:
        sector_etfs = list(config.SECTOR_ETFS.keys())
        etf_data = yf.download(sector_etfs, period="1y", interval="1d", group_by="ticker")
        
        results = []
        for etf in sector_etfs:
            if (etf,) in etf_data.columns.levels[0]:
                data = etf_data[etf].copy()
                
                if data.empty:
                    continue
                
                # Calculate 1-week, 1-month, 3-month, and YTD changes
                current_price = data['Close'].iloc[-1]
                week_ago_price = data['Close'].iloc[-6] if len(data) >= 6 else data['Close'].iloc[0]
                month_ago_price = data['Close'].iloc[-22] if len(data) >= 22 else data['Close'].iloc[0]
                three_month_ago_price = data['Close'].iloc[-66] if len(data) >= 66 else data['Close'].iloc[0]
                start_of_year = data[data.index.year == data.index[0].year].iloc[0]['Close']
                
                week_change = ((current_price / week_ago_price) - 1) * 100
                month_change = ((current_price / month_ago_price) - 1) * 100
                three_month_change = ((current_price / three_month_ago_price) - 1) * 100
                ytd_change = ((current_price / start_of_year) - 1) * 100
                
                results.append({
                    'etf': etf,
                    'sector': config.SECTOR_ETFS[etf],
                    'price': current_price,
                    '1_week_change': week_change,
                    '1_month_change': month_change,
                    '3_month_change': three_month_change,
                    'ytd_change': ytd_change
                })
                
        if results:
            df = pd.DataFrame(results)
            # Sort by 1-month performance from worst to best (for finding downtrodden sectors)
            df = df.sort_values('1_month_change')
            return df
        else:
            return pd.DataFrame(columns=['etf', 'sector', 'price', '1_week_change', '1_month_change', '3_month_change', 'ytd_change'])
            
    except Exception as e:
        logger.error(f"Error calculating sector performances: {e}")
        return pd.DataFrame(columns=['etf', 'sector', 'price', '1_week_change', '1_month_change', '3_month_change', 'ytd_change'])

if __name__ == "__main__":
    # Simple test run
    logger.info("Testing data collection module...")
    
    # Test fetching S&P 500 symbols
    sp500 = get_sp500_symbols()
    logger.info(f"Fetched {len(sp500)} S&P 500 symbols")
    
    # Test fetching historical prices for a few symbols
    symbols = ['AAPL', 'MSFT', 'GOOG']
    prices = get_historical_prices(symbols)
    logger.info(f"Fetched historical prices for {len(prices)} symbols")
    
    # Test market conditions
    market_data = get_market_conditions()
    logger.info(f"Fetched market data for {len(market_data)} indexes/ETFs")
    
    # Test correction check
    in_correction, status = is_market_in_correction()
    logger.info(f"Market status: {status}")
    
    # Test fetching 52-week lows
    lows = fetch_52_week_lows(top_n=10)
    logger.info(f"Fetched {len(lows)} stocks at or near 52-week lows")
    
    logger.info("Data collection module test complete")
