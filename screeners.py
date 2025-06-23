"""
Stock screeners module for the stock screening pipeline.
Implements the screening strategies based on the "15 Tools for Stock Picking" series.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
import datetime
import yfinance as yf
from tqdm import tqdm  # For progress bars

import config
from universe import get_stock_universe
from stock_data import get_historical_prices, fetch_52_week_lows
from market_data import is_market_in_correction, get_sector_performances
from data_processing import (
    calculate_technical_indicators, 
    calculate_price_statistics,
    analyze_debt_and_cash
)
from utils.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Ensure results directory exists
Path(config.RESULTS_DIR).mkdir(parents=True, exist_ok=True)

# Add aliases for screener functions to match what tests are expecting
def price_to_book_screener(*args, **kwargs):
    """Alias for screen_for_price_to_book to maintain test compatibility"""
    return screen_for_price_to_book(*args, **kwargs)

def pe_ratio_screener(*args, **kwargs):
    """Alias for screen_for_pe_ratio to maintain test compatibility"""
    return screen_for_pe_ratio(*args, **kwargs)

def fifty_two_week_low_screener(*args, **kwargs):
    """Alias for screen_for_52_week_lows to maintain test compatibility"""
    return screen_for_52_week_lows(*args, **kwargs)

def get_available_screeners():
    """
    Get a list of all available screener strategy names.
    
    Returns:
        list: List of strategy names (strings)
    """
    # List all the screening functions in this module
    screener_functions = [
        name.replace('screen_for_', '')
        for name in globals()
        if name.startswith('screen_for_') and callable(globals()[name])
    ]
    
    return sorted(screener_functions)


def run_all_screeners(universe_df, strategies=None):
    """
    Run all the specified screeners on the given stock universe.
    Each screener function will fetch its own data directly from the data provider.
    
    Args:
        universe_df (DataFrame): The stock universe being analyzed
        strategies (list, optional): List of strategy names to run, or None for all
    
    Returns:
        dict: Dictionary mapping strategy names to DataFrames with screening results
    """
    # If no strategies specified, run all of them
    if strategies is None:
        strategies = get_available_screeners()
    
    results = {}
    
    for strategy in strategies:
        try:
            # Construct the function name from the strategy name
            func_name = f"screen_for_{strategy}"
            
            # Check if the function exists
            if func_name in globals() and callable(globals()[func_name]):
                logger.info(f"Running {strategy} screener...")
                
                # Call the screener function with only the universe data
                # Each screener will fetch its own data from the provider
                screener_func = globals()[func_name]
                result = screener_func(universe_df=universe_df)
                
                # Store the result
                results[strategy] = result
                
                # Log the number of stocks that passed the screen
                if isinstance(result, pd.DataFrame):
                    logger.info(f"Found {len(result)} stocks matching {strategy} criteria")
            else:
                logger.warning(f"Strategy '{strategy}' not found or not callable")
                
        except Exception as e:
            logger.error(f"Error running {strategy} screener: {e}")
            results[strategy] = pd.DataFrame()  # Empty DataFrame on error
    
    return results

# Standardize the interface for all screeners to use the same parameters
def screen_for_price_to_book(universe_df, max_pb_ratio=None):
    """
    Screen for stocks trading below or near book value.
    Based on Strategy #1: "Understanding Relationship Between Book Value and Share Price"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        max_pb_ratio (float): Maximum price-to-book ratio to include
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if max_pb_ratio is None:
        max_pb_ratio = config.ScreeningThresholds.MAX_PRICE_TO_BOOK_RATIO
    
    logger.info(f"Screening for stocks with P/B ratio <= {max_pb_ratio}...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for low price-to-book ratio", unit="symbol"):
        try:
            # Get company overview data
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
            
            # Check if P/B ratio is available and below threshold
            pb_ratio = company_data.get('PriceToBookRatio')
            if pb_ratio is None or pb_ratio < 0 or np.isnan(float(pb_ratio)):
                continue
            
            # Convert to float if it's a string
            if isinstance(pb_ratio, str):
                pb_ratio = float(pb_ratio)
            
            if pb_ratio <= max_pb_ratio:
                # Get price data to get current price
                price_data = fmp_provider.get_historical_prices(symbol, period="5d")
                if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                    current_price = company_data.get('price', 0)
                else:
                    current_price = price_data[symbol]['Close'].iloc[-1]
                
                # Extract other relevant info
                market_cap = company_data.get('MarketCapitalization', 0)
                company_name = company_data.get('Name', symbol)
                sector = company_data.get('Sector', 'Unknown')
                
                # Calculate book value per share based on available data
                book_value_per_share = current_price / pb_ratio if pb_ratio > 0 else None
                
                # Add to results
                results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'current_price': current_price,
                    'book_value_per_share': book_value_per_share,
                    'price_to_book': pb_ratio,
                    'market_cap': market_cap,
                    'reason': f"Low price to book ratio (P/B = {pb_ratio:.2f})"
                })
                
                logger.info(f"Found {symbol} trading near book value: P/B={pb_ratio:.2f}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for P/B screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by P/B ratio (lowest first)
        df = df.sort_values('price_to_book')
        return df
    else:
        return pd.DataFrame()

def screen_for_pe_ratio(universe_df, max_pe=None):
    """
    Screen for stocks with low P/E ratios.
    Based on Strategy #2: "Never Lose Sight of P/E Multiples!"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        max_pe (float): Maximum P/E ratio to include
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if max_pe is None:
        max_pe = config.ScreeningThresholds.MAX_PE_RATIO
    
    logger.info(f"Screening for stocks with P/E ratio <= {max_pe}...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for low P/E ratio", unit="symbol"):
        try:
            # Get company overview data
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
            
            # Check if P/E ratio is available and below threshold
            pe_ratio = company_data.get('PERatio')
            if pe_ratio is None or pe_ratio == '':
                continue
            
            # Convert to float if it's a string
            if isinstance(pe_ratio, str):
                pe_ratio = float(pe_ratio)
            
            # Handle negative PE ratios - typically excluded
            if pe_ratio <= 0:
                continue
                
            if pe_ratio <= max_pe:
                # Get price data to get current price
                price_data = fmp_provider.get_historical_prices(symbol, period="5d")
                if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                    current_price = company_data.get('price', 0)
                else:
                    current_price = price_data[symbol]['Close'].iloc[-1]
                
                # Extract other relevant info
                market_cap = company_data.get('MarketCapitalization', 0)
                company_name = company_data.get('Name', symbol)
                sector = company_data.get('Sector', 'Unknown')
                
                # Calculate forward PE if available
                eps = company_data.get('EPS')
                forward_pe = None
                if eps and eps != '' and float(eps) > 0:
                    forward_pe = current_price / float(eps)
                
                # Add to results
                results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'current_price': current_price,
                    'pe_ratio': pe_ratio,
                    'forward_pe': forward_pe,
                    'market_cap': market_cap,
                    'reason': f"Low P/E ratio (P/E = {pe_ratio:.2f})"
                })
                
                logger.info(f"Found {symbol} with low P/E ratio: {pe_ratio:.2f}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for P/E screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by P/E ratio (lowest first)
        df = df.sort_values('pe_ratio')
        return df
    else:
        return pd.DataFrame()

def screen_for_52_week_lows(universe_df, min_pct_off_high=None, max_pct_above_low=None):
    """
    Screen for stocks near their 52-week lows.
    Based on Strategy #3: "Know When & Where to Mine for 52-Week Lows"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_pct_off_high (float): Minimum percentage off 52-week high
        max_pct_above_low (float): Maximum percentage above 52-week low
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if max_pct_above_low is None:
        max_pct_above_low = config.ScreeningThresholds.MAX_PERCENT_OFF_52_WEEK_LOW
        
    logger.info(f"Screening for stocks near 52-week lows (max {max_pct_above_low}% above low)...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # First check if market is in correction - this strategy works best during corrections
    try:
        in_correction, status = is_market_in_correction()
        logger.info(f"Market status: {status}")
    except Exception as e:
        logger.error(f"Error checking market correction status: {e}")
        # Continue anyway, since we might still want to find stocks near 52-week lows
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for stocks near 52-week lows", unit="symbol"):
        try:
            # Get historical price data for the last year
            price_data = fmp_provider.get_historical_prices(symbol, period="1y")
            
            # Skip if we couldn't get price data
            if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                continue
            
            data = price_data[symbol]
            
            # Calculate 52-week high, low, and current price
            high_52week = data['High'].max()
            low_52week = data['Low'].min()
            current_price = data['Close'].iloc[-1]
            
            # Calculate percentage off high and above low
            pct_off_high = ((high_52week - current_price) / high_52week) * 100
            pct_above_low = ((current_price - low_52week) / low_52week) * 100
            
            # Check if the stock meets the criteria
            if pct_above_low <= max_pct_above_low:
                # Additional filter if min_pct_off_high is provided
                if min_pct_off_high is not None and pct_off_high < min_pct_off_high:
                    continue
                
                # Get company overview
                company_data = fmp_provider.get_company_overview(symbol)
                
                # Extract relevant info
                market_cap = company_data.get('MarketCapitalization', 0) if company_data else 0
                company_name = company_data.get('Name', symbol) if company_data else symbol
                sector = company_data.get('Sector', 'Unknown') if company_data else universe_df.loc[universe_df['symbol'] == symbol, 'gics_sector'].values[0] if 'gics_sector' in universe_df.columns and symbol in universe_df['symbol'].values else 'Unknown'
                
                # Calculate YTD change
                try:
                    # Get the first trading day of the year
                    start_year_data = data[data.index.year == data.index[0].year].iloc[0]
                    ytd_change = ((current_price / start_year_data['Close']) - 1) * 100
                except Exception:
                    ytd_change = None
                
                # Add to results
                results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'current_price': current_price,
                    '52_week_high': high_52week,
                    '52_week_low': low_52week,
                    'pct_off_high': pct_off_high,
                    'pct_above_low': pct_above_low,
                    'ytd_change': ytd_change,
                    'market_cap': market_cap,
                    'reason': f"Near 52-week low ({pct_above_low:.2f}% above low)"
                })
                
                logger.info(f"Found {symbol} near 52-week low: {pct_above_low:.2f}% above low, {pct_off_high:.2f}% off high")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for 52-week low screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by percentage above low (lowest first)
        df = df.sort_values('pct_above_low')
        return df
    else:
        return pd.DataFrame()

def screen_for_fallen_ipos(universe_df, max_years_since_ipo=3, min_pct_off_high=70):
    """
    Screen for fallen IPOs that have dropped significantly from their highs.
    Based on Strategy #4: "How to Make a Fortune on IPOs—NEVER Buy One!"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        max_years_since_ipo (int): Maximum years since IPO date
        min_pct_off_high (float): Minimum percentage off post-IPO high
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    logger.info(f"Screening for fallen IPOs dropped >={min_pct_off_high}% from high...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # This requires specialized data on IPO dates
    # For this implementation, we'll use a simplification based on available data
    
    # Use the provided universe
    symbols = universe_df['symbol'].tolist()
    
    # Note: We're using the provided universe rather than hardcoding NASDAQ/Russell
    # This allows more flexibility in choosing the universe
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Current date for reference
    current_date = datetime.datetime.now()
    cutoff_date = current_date - datetime.timedelta(days=max_years_since_ipo*365)
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for fallen IPOs", unit="symbol"):
        try:
            # Get historical price data
            price_data = fmp_provider.get_historical_prices(symbol, period=f"{max_years_since_ipo+1}y")
            
            # Skip if we couldn't get price data
            if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                continue
            
            data = price_data[symbol]
            
            # Check if data history is short enough to be a recent IPO
            first_date = data.index[0]
            if first_date < cutoff_date:
                # Too old, likely not a recent IPO
                continue
            
            # Find the all-time high since IPO and current price
            all_time_high = data['High'].max()
            current_price = data['Close'].iloc[-1]
            
            # Calculate percentage off high
            pct_off_high = ((all_time_high - current_price) / all_time_high) * 100
              # Check if it meets the threshold
            if pct_off_high >= min_pct_off_high:
                try:
                    # Get company overview
                    company_data = fmp_provider.get_company_overview(symbol)
                    
                    # Extract relevant info
                    market_cap = company_data.get('MarketCapitalization', 0) if company_data else 0
                    company_name = company_data.get('Name', symbol) if company_data else symbol
                    
                    # Check if it's profitable yet
                    pe_ratio = company_data.get('PERatio', None) if company_data else None
                    if isinstance(pe_ratio, str) and pe_ratio != '':
                        pe_ratio = float(pe_ratio)
                    is_profitable = pe_ratio is not None and not np.isnan(pe_ratio) if isinstance(pe_ratio, float) else False
                except Exception as e:
                    logger.error(f"Error getting company data for {symbol}: {e}")
                    # If provider fails to return data, stop execution
                    raise Exception(f"Data provider failed for symbol {symbol}: {e}")
                    
                # Add to results
                results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'ipo_date': first_date.strftime('%Y-%m-%d'),
                    'days_since_ipo': (current_date - first_date).days,
                    'all_time_high': all_time_high,
                    'current_price': current_price,
                    'pct_off_high': pct_off_high,
                    'is_profitable': is_profitable,
                    'market_cap': market_cap,
                    'reason': f"Fallen IPO ({pct_off_high:.2f}% off high)"
                })
                
                logger.info(f"Found fallen IPO {symbol}: {pct_off_high:.2f}% off high")
        except Exception as e:
            logger.error(f"Error processing {symbol} for fallen IPO screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
            
    # Create DataFrame from results
    if results:
        results_df = pd.DataFrame(results)
        # Sort by percentage off high
        results_df = results_df.sort_values('pct_off_high', ascending=False)
        logger.info(f"Found {len(results_df)} fallen IPOs")
        return results_df
    else:
        logger.info("No fallen IPOs found meeting the criteria")
        return pd.DataFrame()
