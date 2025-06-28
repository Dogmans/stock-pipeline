"""
Stock screeners module for the stock screening pipeline.
Implements the screening strategies based on the "15 Tools for Stock Picking" series.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import yfinance as yf
from tqdm import tqdm  # For progress bars

import config
from universe import get_stock_universe
from cache_config import cache  # Import cache for force_refresh
from stock_data import get_historical_prices, fetch_52_week_lows
from market_data import is_market_in_correction, get_sector_performances
from technical_indicators import calculate_technical_indicators
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

def screen_for_turnaround_candidates(universe_df, force_refresh=False):
    """
    Screen for companies showing signs of financial turnaround or improvement.
    
    This screener looks for companies that have genuinely "turned the corner" from financial distress,
    such as:
    1. EPS trend changing from negative to positive (true turnaround)
    2. Revenue returning to growth after declines
    3. Margins recovering from compression
    4. Balance sheet strengthening after deterioration
    5. Debt reduction after increases
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        force_refresh (bool): Whether to bypass cache for API calls
        
    Returns:
        DataFrame: Stocks meeting the turnaround criteria
    """
    logger.info(f"Screening for companies that have truly 'turned the corner'...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for turnaround candidates", unit="symbol"):
        try:
            # Get company overview data
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
                    # Get quarterly financial statements (last 8 quarters)
            if force_refresh:
                # Clear cache before requesting new data
                try:
                    cache.delete(fmp_provider.get_income_statement, symbol, False)
                except:
                    pass
                    
            income_statements = fmp_provider.get_income_statement(
                symbol, annual=False
            )
            
            if income_statements.empty or len(income_statements) < config.ScreeningThresholds.QUARTERS_RETURNED:  # Need minimum X quarters
                continue
                
            # Check for turnaround signals
            
            # 1. EPS TURNAROUND ANALYSIS - Looking for transition from negative to positive
            if 'eps' not in income_statements.columns:
                logger.warning(f"No 'eps' field in income statements for {symbol}")
                continue
                
            eps_values = income_statements['eps'].tolist()
            
            # True turnaround: Recent quarters positive after previous negative quarters
            recent_quarters_positive = eps_values[0] > 0 and eps_values[1] > 0
            historical_quarters_negative = sum(1 for eps in eps_values[2:6] if eps < 0) >= 2
            
            true_eps_turnaround = recent_quarters_positive and historical_quarters_negative
            
            # Strong improvement: Consecutive increases in EPS with significant growth
            if len(eps_values) >= 4 and all(eps_values[i] > 0 for i in range(4)):
                eps_growth_rates = [(eps_values[i]/eps_values[i+1] - 1) * 100 for i in range(3) 
                                   if eps_values[i+1] > 0]  # Avoid division by zero
                strong_eps_improvement = len(eps_growth_rates) >= 3 and all(rate > 15 for rate in eps_growth_rates)
            else:
                strong_eps_improvement = False
                
            # Calculate EPS turnaround metrics for display
            eps_yoy_change = ((eps_values[0]/eps_values[4])-1)*100 if len(eps_values) >= 5 and eps_values[4] > 0 else None
            
            # 2. REVENUE TURNAROUND ANALYSIS - Looking for return to growth after decline
            revenue_field = 'revenue'
            if revenue_field not in income_statements.columns:
                revenue_field = 'totalRevenue'  # Try alternative field name
                if revenue_field not in income_statements.columns:
                    logger.warning(f"No revenue field in income statements for {symbol}")
                    continue
                    
            revenue_values = income_statements[revenue_field].tolist()
            
            # Calculate YoY quarterly growth rates
            if len(revenue_values) >= 8:  # Need 2 years of data
                yoy_growth_rates = [(revenue_values[i]/revenue_values[i+4] - 1) * 100 
                                   for i in range(4) if revenue_values[i+4] > 0]
                
                # Previous YoY growth was negative, but now turned positive
                if len(yoy_growth_rates) >= 3:
                    previous_decline = any(rate < 0 for rate in yoy_growth_rates[1:3])
                    current_growth = yoy_growth_rates[0] > 0
                    revenue_turnaround = previous_decline and current_growth
                    
                    # Also check for reacceleration (regardless of negative/positive)
                    revenue_reaccelerating = yoy_growth_rates[0] > yoy_growth_rates[1] > yoy_growth_rates[2]
                    
                    # Calculate revenue growth for display
                    latest_yoy_growth = yoy_growth_rates[0] if yoy_growth_rates else None
                else:
                    revenue_turnaround = False
                    revenue_reaccelerating = False
                    latest_yoy_growth = None
            else:
                revenue_turnaround = False
                revenue_reaccelerating = False
                latest_yoy_growth = None
                
            # 3. MARGIN IMPROVEMENT ANALYSIS - Looking for margin recovery
            gross_profit_field = 'grossProfit'
            if gross_profit_field in income_statements.columns and revenue_field in income_statements.columns:
                # Calculate gross margins for last 8 quarters
                gross_margins = income_statements[gross_profit_field] / income_statements[revenue_field]
                
                if len(gross_margins) >= 8:
                    # Margins bottomed out and now recovering
                    margin_bottomed = min(gross_margins[:3]) > min(gross_margins[3:6])
                    recent_margin_improving = gross_margins.iloc[0] > gross_margins.iloc[1]
                    
                    # Significant improvement from recent low
                    low_point = min(gross_margins.iloc[1:6])
                    significant_margin_recovery = gross_margins.iloc[0] > (1.1 * low_point)  # 10% better than low
                    
                    margins_recovering = recent_margin_improving and significant_margin_recovery
                    
                    # Calculate margin metrics for display
                    current_margin = gross_margins.iloc[0] * 100  # Convert to percentage
                    margin_change = ((gross_margins.iloc[0] / gross_margins.iloc[4]) - 1) * 100  # YoY change
                else:
                    margins_recovering = False
                    current_margin = None
                    margin_change = None
            else:
                margins_recovering = False
                current_margin = None
                margin_change = None
                  # 4. BALANCE SHEET IMPROVEMENT ANALYSIS
            if force_refresh:
                # Clear cache before requesting new data
                try:
                    cache.delete(fmp_provider.get_balance_sheet, symbol, False)
                except:
                    pass
                    
            balance_sheets = fmp_provider.get_balance_sheet(
                symbol, annual=False
            )
            
            if balance_sheets.empty or len(balance_sheets) < 4:
                cash_improvement = False
                debt_reduction = False
                cash_change = None
                debt_change = None
            else:
                # Look for cash improvement
                cash_field = 'cash' if 'cash' in balance_sheets.columns else None
                if cash_field:
                    cash_values = balance_sheets[cash_field].tolist()
                    if len(cash_values) >= 4:
                        # Cash was previously declining but is now increasing
                        previous_cash_declining = cash_values[2] < cash_values[3]
                        recent_cash_growing = cash_values[0] > cash_values[1]
                        cash_improvement = previous_cash_declining and recent_cash_growing
                        
                        # Calculate cash change metric for display
                        cash_change = ((cash_values[0] / cash_values[2]) - 1) * 100 if cash_values[2] > 0 else None
                    else:
                        cash_improvement = False
                        cash_change = None
                else:
                    cash_improvement = False
                    cash_change = None
                
                # Look for debt reduction
                debt_field = 'totalDebt' if 'totalDebt' in balance_sheets.columns else None
                if debt_field:
                    debt_values = balance_sheets[debt_field].tolist()
                    if len(debt_values) >= 4:
                        # Debt was previously increasing but is now decreasing
                        previous_debt_increasing = debt_values[2] > debt_values[3]
                        recent_debt_decreasing = debt_values[0] < debt_values[1]
                        debt_reduction = previous_debt_increasing and recent_debt_decreasing
                        
                        # Calculate debt change metric for display
                        debt_change = ((debt_values[0] / debt_values[2]) - 1) * 100 if debt_values[2] > 0 else None
                    else:
                        debt_reduction = False
                        debt_change = None
                else:
                    debt_reduction = False
                    debt_change = None
            
            # ENHANCED SCORING SYSTEM - More weight for true turnarounds
            turnaround_score = 0
            factors = []  # Track which factors contributed to score
              # Primary turnaround signals
            if true_eps_turnaround:
                turnaround_score += 5  # Major signal - transition from negative to positive
                factors.append("negative-to-positive EPS")
            elif strong_eps_improvement:
                turnaround_score += 2  # Minor signal - continuous improvement
                factors.append("strong EPS growth")
                
            if revenue_turnaround:
                turnaround_score += 4  # Major signal - return to growth after decline
                factors.append("revenue recovery")
            elif revenue_reaccelerating:
                turnaround_score += 2  # Minor signal - just acceleration
                factors.append("revenue acceleration")
                
            if margins_recovering:
                turnaround_score += 3  # Significant signal - margin expansion after compression
                factors.append("margin recovery")
                
            if cash_improvement:
                turnaround_score += 2  # Moderate signal - cash position strengthening
                factors.append("cash improvement")
                
            if debt_reduction:
                turnaround_score += 2  # Moderate signal - deleveraging
                factors.append("debt reduction")
                
            # Higher minimum threshold to ensure true turnaround cases
            if turnaround_score >= 5:
                # Create detailed reason text for reporting
                has_true_turnaround = true_eps_turnaround or revenue_turnaround
                primary_factor = factors[0] if factors else "multiple factors"
                score_text = f"Score: {turnaround_score} - {', '.join(factors)}"
                  # Add EPS transition text
                if true_eps_turnaround:
                    eps_trend_text = "Negative-to-Positive EPS"
                elif strong_eps_improvement:
                    eps_trend_text = f"Strong EPS growth: {eps_yoy_change:.1f}%" if eps_yoy_change else "Strong EPS growth"
                else:
                    eps_trend_text = "Improving EPS"
                
                results.append({
                    'symbol': symbol,
                    'company_name': company_data.get('Name', symbol),
                    'sector': company_data.get('Sector', 'Unknown'),
                    'turnaround_score': turnaround_score,
                    'true_turnaround': has_true_turnaround,  # Flag for sorting
                    'eps_trend': eps_trend_text,
                    'revenue_trend': ('Recovery' if revenue_turnaround else 
                                    'Accelerating' if revenue_reaccelerating else 'Stable'),
                    'margins': 'Recovering' if margins_recovering else 'Stable',
                    'balance_sheet': ('Strengthening' if cash_improvement or debt_reduction else 'Stable'),                    'latest_eps': eps_values[0] if len(eps_values) > 0 else None,
                    'reason': score_text,
                    'primary_factor': primary_factor
                })
                
        except Exception as e:
            logger.error(f"Error screening {symbol} for turnaround: {e}")
            continue
    
    # Convert results to DataFrame
    if not results:
        return pd.DataFrame()
        
    result_df = pd.DataFrame(results)
      # Sort first by true turnaround status, then by score
    if not result_df.empty:
        if 'true_turnaround' in result_df.columns and 'turnaround_score' in result_df.columns:
            result_df = result_df.sort_values(['true_turnaround', 'turnaround_score'], 
                                             ascending=[False, False])
        elif 'turnaround_score' in result_df.columns:
            result_df = result_df.sort_values('turnaround_score', ascending=False)
            
        # Drop the helper column used for sorting
        if 'true_turnaround' in result_df.columns:
            result_df = result_df.drop(columns=['true_turnaround'])
    
    logger.info(f"Found {len(result_df)} true turnaround candidates")
    return result_df

def screen_for_peg_ratio(universe_df=None, max_peg_ratio=1.0, min_growth=5.0, force_refresh=False):
    """
    Screen for stocks with low PEG (Price/Earnings to Growth) ratios.
    
    The PEG ratio is calculated as (P/E ratio) / (Expected Growth Rate).
    A stock with a PEG ratio below 1.0 is potentially undervalued relative to its growth.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe.
        max_peg_ratio (float): Maximum PEG ratio to include in results (default: 1.0).
        min_growth (float): Minimum expected growth rate percentage (default: 5.0%).
        force_refresh (bool): Whether to force refresh data from API.
        
    Returns:
        pd.DataFrame: DataFrame containing screening results with columns for symbol,
                     company name, sector, P/E ratio, growth rate, PEG ratio, etc.
    """
    logger.info("Running PEG ratio screener")
    
    # Use either provided universe or get the sp500 by default
    if universe_df is None:
        universe_df = get_stock_universe()
    
    # Import providers here to avoid circular imports
    import data_providers
    fmp_provider = data_providers.get_provider("financial_modeling_prep")
    
    results = []
    
    # Process each symbol
    for _, row in tqdm(universe_df.iterrows(), total=len(universe_df), desc="Screening for PEG ratio"):
        symbol = row['symbol']
        
        try:
            # Get company overview data which contains P/E and other metrics
            company_data = fmp_provider.get_company_overview(symbol, force_refresh=force_refresh)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
            
            # Get P/E ratio from company data
            pe_ratio = company_data.get('PERatio')
            if pe_ratio is None or pe_ratio < 0 or np.isnan(float(pe_ratio)):
                continue
                
            # Convert to float if it's a string
            if isinstance(pe_ratio, str):
                pe_ratio = float(pe_ratio)
            
            # Get growth rate - from either EPS Growth or Revenue Growth
            # Try to get EPS growth first
            eps_growth = company_data.get('EPSGrowth')
            revenue_growth = company_data.get('RevenueGrowth')
            
            # Use quarterly data if available for more recent growth figures
            income_stmt = fmp_provider.get_income_statement(symbol, annual=False, force_refresh=force_refresh)
            
            growth_rate = None
            growth_type = None
            
            # Calculate growth rate from quarterly data if available
            if income_stmt is not None and len(income_stmt) >= 4:
                try:
                    # Calculate YoY quarterly EPS growth
                    current_eps = income_stmt.iloc[0].get('eps', None)
                    year_ago_eps = income_stmt.iloc[4].get('eps', None)
                    
                    if current_eps is not None and year_ago_eps is not None and year_ago_eps != 0:
                        if year_ago_eps > 0 and current_eps > 0:
                            eps_growth = ((current_eps / year_ago_eps) - 1) * 100
                            growth_rate = eps_growth
                            growth_type = "EPS YoY"
                except (IndexError, KeyError, TypeError, ZeroDivisionError):
                    pass
            
            # Fall back to company_data growth rates if quarterly calculation failed
            if growth_rate is None:
                if eps_growth is not None and not np.isnan(float(eps_growth)):
                    growth_rate = float(eps_growth) * 100  # Convert to percentage
                    growth_type = "EPS"
                elif revenue_growth is not None and not np.isnan(float(revenue_growth)):
                    growth_rate = float(revenue_growth) * 100  # Convert to percentage
                    growth_type = "Revenue"
            
            # Skip if growth rate is not available or below minimum
            if growth_rate is None or growth_rate < min_growth:
                continue
            
            # Calculate PEG ratio
            peg_ratio = pe_ratio / growth_rate
            
            # Skip if PEG is above our threshold
            if peg_ratio > max_peg_ratio:
                continue
            
            # Get other relevant company information
            company_name = company_data.get('Name', symbol)
            sector = company_data.get('Sector', 'Unknown')
            market_cap = company_data.get('MarketCapitalization', 0)
            
            # Format the reason string
            reason = f"PEG: {peg_ratio:.2f} (P/E: {pe_ratio:.2f}, Growth: {growth_rate:.1f}% {growth_type})"
            
            # Add to results
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'pe_ratio': pe_ratio,
                'growth_rate': growth_rate,
                'growth_type': growth_type,
                'peg_ratio': peg_ratio,
                'market_cap': market_cap,
                'reason': reason
            })
            
        except Exception as e:
            logger.warning(f"Error processing {symbol} for PEG ratio: {str(e)}")
    
    # Convert results to DataFrame
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    
    # Sort by PEG ratio (ascending)
    if not result_df.empty:
        result_df = result_df.sort_values('peg_ratio')
    
    logger.info(f"Found {len(result_df)} stocks with favorable PEG ratios")
    return result_df
