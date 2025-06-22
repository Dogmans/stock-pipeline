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
    for symbol in symbols:
        try:
            # Get company overview data
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
            
            # Check if P/B ratio is available and below threshold
            pb_ratio = company_data.get('PriceToBookRatio')
            if pb_ratio is None or np.isnan(float(pb_ratio)):
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
    for symbol in symbols:
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
    for symbol in symbols:
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
    for symbol in symbols:
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
                
                # Add to results
                results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'current_price': current_price,
                    'all_time_high': all_time_high,
                    'first_data_date': first_date.strftime('%Y-%m-%d'),
                    'pct_off_high': pct_off_high,
                    'is_profitable': is_profitable,
                    'pe_ratio': pe_ratio,
                    'market_cap': market_cap,
                    'reason': f"Fallen IPO ({pct_off_high:.1f}% below peak, IPO: {first_date.strftime('%Y-%m-%d')})"
                })
                
                logger.info(f"Found fallen IPO {symbol}: {pct_off_high:.2f}% off high")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for fallen IPO screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by percentage off high (highest first)
        df = df.sort_values('pct_off_high', ascending=False)
        return df
    else:
        return pd.DataFrame()

def screen_for_cash_rich_biotech(universe_df, min_cash_to_mc_ratio=None):
    """
    Screen for biotech stocks with high cash reserves relative to market cap.
    Based on Strategy #7: "How to Use AI to Calculate Debt, Cash Runway, & Burn Rate"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_cash_to_mc_ratio (float): Minimum cash to market cap ratio
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if min_cash_to_mc_ratio is None:
        min_cash_to_mc_ratio = config.ScreeningThresholds.BIOTECH_MIN_CASH_TO_MARKET_CAP
    
    logger.info(f"Screening for biotech stocks with cash >= {min_cash_to_mc_ratio*100}% of market cap...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
      # Get biotech stocks - this could be from IBB ETF holdings or by sector
    # For simplicity, we'll filter the stock universe by biotech sector
    biotech_stocks = universe_df[universe_df['gics_sector'] == 'Health Care']
    
    # If no biotech stocks found, use all stocks
    if biotech_stocks.empty:
        biotech_stocks = universe_df
        
    symbols = biotech_stocks['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in symbols:
        try:
            # Get company overview
            company_data = fmp_provider.get_company_overview(symbol)
            if not company_data:
                continue
                
            # Skip if no market cap data
            market_cap = company_data.get('MarketCapitalization', 0)
            if isinstance(market_cap, str) and market_cap != '':
                market_cap = float(market_cap)
            if not market_cap or market_cap <= 0:
                continue
            
            # Get balance sheet to find cash reserves
            balance_sheet = fmp_provider.get_balance_sheet(symbol)
            if balance_sheet.empty:
                continue
                
            # Get the most recent balance sheet entry
            latest_bs = balance_sheet.iloc[0]
            
            # Get cash and short-term investments
            cash = latest_bs.get('cash', 0)
            short_term_investments = latest_bs.get('shortTermInvestments', 0)
            total_cash = cash + short_term_investments
            
            # Calculate cash to market cap ratio
            cash_to_mc_ratio = total_cash / market_cap
            
            # Check if it meets the threshold
            if cash_to_mc_ratio >= min_cash_to_mc_ratio:
                # Get current price
                price_data = fmp_provider.get_historical_prices(symbol, period="5d")
                if symbol in price_data and not price_data[symbol].empty:
                    current_price = price_data[symbol]['Close'].iloc[-1]
                else:
                    current_price = 0
                
                # Calculate debt metrics
                total_debt = latest_bs.get('longTermDebt', 0) + latest_bs.get('shortTermDebt', 0) if 'shortTermDebt' in latest_bs else latest_bs.get('longTermDebt', 0)
                total_equity = latest_bs.get('totalShareholderEquity', 0)
                debt_to_equity = total_debt / total_equity if total_equity > 0 else float('inf')
                
                # Get income statement for burn rate calculation
                income_stmt = fmp_provider.get_income_statement(symbol)
                
                # Calculate monthly burn rate and cash runway
                monthly_burn_rate = 0
                cash_runway_months = None
                
                if not income_stmt.empty:
                    # Get the latest quarterly net income and annualize it
                    latest_income = income_stmt.iloc[0]
                    net_income = latest_income.get('netIncome', 0)
                    
                    # If company is losing money, calculate burn rate
                    if net_income < 0:
                        # Quarterly burn rate (negative net income is cash burn)
                        burn_rate = abs(net_income)
                        monthly_burn_rate = burn_rate / 3  # Assuming quarterly data
                        
                        # Cash runway in months
                        cash_runway_months = total_cash / monthly_burn_rate if monthly_burn_rate > 0 else float('inf')
                
                # Extract relevant info
                company_name = company_data.get('Name', symbol)
                
                # Add to results
                results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'current_price': current_price,
                    'market_cap': market_cap,
                    'total_cash': total_cash,
                    'cash_to_mc_ratio': cash_to_mc_ratio,
                    'cash_runway_months': cash_runway_months,
                    'monthly_burn_rate': monthly_burn_rate,
                    'total_debt': total_debt,
                    'debt_to_equity': debt_to_equity,
                    'reason': f"Cash-rich biotech ({cash_to_mc_ratio:.2f}x cash/market cap)"
                })
                
                logger.info(f"Found cash-rich biotech {symbol}: {cash_to_mc_ratio:.2f} cash/MC ratio")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for cash-rich biotech screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by cash to market cap ratio (highest first)
        df = df.sort_values('cash_to_mc_ratio', ascending=False)
        return df
    else:
        return pd.DataFrame()

def screen_for_sector_corrections(universe_df, **kwargs):
    """
    Screen for stocks in sectors that are in correction or oversold.
    Based on Strategy #11: "Understanding Potential Catalysts, Headwinds, Tailwinds"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        **kwargs: Additional keyword arguments
        
    Returns:
        DataFrame: Stocks in sectors that are in correction, with sector performance data
    """
    logger.info("Screening for stocks in sectors experiencing corrections...")
    
    # Get sector performance data directly
    sector_perf = get_sector_performances()
    
    # Sort by 1-month performance (worst first)
    if not sector_perf.empty:
        sector_perf = sector_perf.sort_values('1_month_change')
        
        # Add a column that identifies which sectors are in correction
        sector_perf['is_correction'] = sector_perf['1_month_change'] <= -10
        sector_perf['is_bear_market'] = sector_perf['1_month_change'] <= -20
        
        # Get sectors in correction
        correcting_sectors = sector_perf[sector_perf['is_correction']]['sector'].tolist()
        bear_market_sectors = sector_perf[sector_perf['is_bear_market']]['sector'].tolist()
        
        if correcting_sectors:
            logger.info(f"Sectors in correction: {correcting_sectors}")
            if bear_market_sectors:
                logger.info(f"Sectors in bear market: {bear_market_sectors}")
        else:
            logger.info("No sectors in correction found")
            return pd.DataFrame()
          # Use universe data to find stocks in the correcting sectors
        
        if 'sector' in universe_df.columns or 'gics_sector' in universe_df.columns:
            sector_col = 'gics_sector' if 'gics_sector' in universe_df.columns else 'sector'
            stocks_in_correction = universe_df[universe_df[sector_col].isin(correcting_sectors)].copy()
            
            # Add sector performance data
            for sector in correcting_sectors:
                sector_info = sector_perf[sector_perf['sector'] == sector].iloc[0]
                mask = stocks_in_correction[sector_col] == sector
                stocks_in_correction.loc[mask, 'sector_1m_change'] = sector_info['1_month_change']
                stocks_in_correction.loc[mask, 'sector_3m_change'] = sector_info.get('3_month_change', 0)
                stocks_in_correction.loc[mask, 'sector_status'] = 'Bear Market' if sector_info['is_bear_market'] else 'Correction'
                # Add a reason column
                stocks_in_correction.loc[mask, 'reason'] = f"{sector} sector in {'bear market' if sector_info['is_bear_market'] else 'correction'} ({sector_info['1_month_change']:.1f}% 1-month change)"
            
            # Sort by sector performance (worst first) then by stock metrics
            stocks_in_correction = stocks_in_correction.sort_values(['sector_1m_change', sector_col])
            
            if not stocks_in_correction.empty:
                logger.info(f"Found {len(stocks_in_correction)} stocks in {len(stocks_in_correction[sector_col].unique())} correcting sectors")
                # Ensure symbol column exists
                if 'symbol' not in stocks_in_correction.columns and 'Symbol' in stocks_in_correction.columns:
                    stocks_in_correction['symbol'] = stocks_in_correction['Symbol']
                return stocks_in_correction
            
            logger.warning(f"No stocks found in correcting sectors using universe data")
        else:
            logger.warning("Universe data doesn't contain sector information")
        
        # If we reach here, we couldn't find any stocks - create a fallback DataFrame with sector ETFs
        # So the reporting system can still use the sector data
        logger.info("Creating fallback DataFrame with sector ETFs")
        sectors_df = sector_perf[sector_perf['is_correction']].copy()
        
        if not sectors_df.empty:
            etfs = pd.DataFrame()
            etfs['symbol'] = sectors_df['sector'] + " ETF"
            etfs['company_name'] = sectors_df['sector'] + " Sector ETF"
            etfs['sector'] = sectors_df['sector'] 
            etfs['sector_1m_change'] = sectors_df['1_month_change']
            etfs['sector_3m_change'] = sectors_df.get('3_month_change', pd.Series([0] * len(sectors_df)))
            etfs['sector_status'] = ['Bear Market' if x else 'Correction' for x in sectors_df['is_bear_market']]
            etfs['reason'] = [f"Sector in {'bear market' if x else 'correction'} ({y:.1f}% 1-month change)" 
                             for x, y in zip(sectors_df['is_bear_market'], sectors_df['1_month_change'])]
            
            logger.info(f"Created {len(etfs)} sector ETF entries as fallback")
            return etfs
    
    logger.warning("No sector performance data available")
    return pd.DataFrame()

def screen_for_combined(universe_df):
    """
    Combine multiple screening strategies and assign scores to stocks.
    This helps identify stocks that meet multiple criteria.
    
    Args:
        universe_df (DataFrame): Which universe to screen (required)
        
    Returns:
        DataFrame: Stocks with scores based on meeting various criteria
    """
    logger.info("Running combined screener...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Run individual screeners
    book_value_stocks = screen_for_price_to_book(universe_df=universe_df)
    low_pe_stocks = screen_for_pe_ratio(universe_df=universe_df)
    lows_52week_stocks = screen_for_52_week_lows(universe_df=universe_df)
    fallen_ipos = screen_for_fallen_ipos(universe_df=universe_df)
    cash_rich_biotech = screen_for_cash_rich_biotech(universe_df=universe_df)
    
    # Create a set of all symbols
    all_symbols = set()
    if not book_value_stocks.empty:
        all_symbols.update(book_value_stocks['symbol'])
    if not low_pe_stocks.empty:
        all_symbols.update(low_pe_stocks['symbol'])
    if not lows_52week_stocks.empty:
        all_symbols.update(lows_52week_stocks['symbol'])
    if not fallen_ipos.empty:
        all_symbols.update(fallen_ipos['symbol'])
    if not cash_rich_biotech.empty:
        all_symbols.update(cash_rich_biotech['symbol'])
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Create a DataFrame with all symbols
    results = []
    for symbol in all_symbols:
        result = {'symbol': symbol}
        
        # Check if it meets book value criteria
        if not book_value_stocks.empty and symbol in book_value_stocks['symbol'].values:
            row = book_value_stocks[book_value_stocks['symbol'] == symbol].iloc[0]
            result['book_value_per_share'] = row.get('book_value_per_share')
            result['price_to_book'] = row.get('price_to_book')
            result['meets_book_value_criteria'] = True
        else:
            result['meets_book_value_criteria'] = False
        
        # Check if it meets PE ratio criteria
        if not low_pe_stocks.empty and symbol in low_pe_stocks['symbol'].values:
            row = low_pe_stocks[low_pe_stocks['symbol'] == symbol].iloc[0]
            result['pe_ratio'] = row.get('pe_ratio')
            result['meets_pe_ratio_criteria'] = True
        else:
            result['meets_pe_ratio_criteria'] = False
        
        # Check if it meets 52-week low criteria
        if not lows_52week_stocks.empty and symbol in lows_52week_stocks['symbol'].values:
            row = lows_52week_stocks[lows_52week_stocks['symbol'] == symbol].iloc[0]
            result['pct_off_high'] = row.get('pct_off_high')
            result['pct_above_low'] = row.get('pct_above_low')
            result['meets_52week_low_criteria'] = True
        else:
            result['meets_52week_low_criteria'] = False
        
        # Check if it's a fallen IPO
        if not fallen_ipos.empty and symbol in fallen_ipos['symbol'].values:
            row = fallen_ipos[fallen_ipos['symbol'] == symbol].iloc[0]
            result['pct_off_high'] = row.get('pct_off_high')
            result['first_data_date'] = row.get('first_data_date')
            result['is_fallen_ipo'] = True
        else:
            result['is_fallen_ipo'] = False
        
        # Check if it's a cash-rich biotech
        if not cash_rich_biotech.empty and symbol in cash_rich_biotech['symbol'].values:
            row = cash_rich_biotech[cash_rich_biotech['symbol'] == symbol].iloc[0]
            result['cash_to_mc_ratio'] = row.get('cash_to_mc_ratio')
            result['cash_runway_months'] = row.get('cash_runway_months')
            result['is_cash_rich_biotech'] = True
        else:
            result['is_cash_rich_biotech'] = False
        
        # Calculate a score based on how many criteria it meets
        score = 0
        if result['meets_book_value_criteria']:
            score += 1
        if result['meets_pe_ratio_criteria']:
            score += 1
        if result['meets_52week_low_criteria']:
            score += 1
        if result['is_fallen_ipo']:
            score += 1
        if result['is_cash_rich_biotech']:
            score += 1
        
        result['score'] = score
        
        # Build a reason string based on criteria met
        reasons = []
        if result['meets_book_value_criteria']:
            reasons.append(f"Low P/B ratio ({result.get('price_to_book', 'N/A')})")
        if result['meets_pe_ratio_criteria']:
            reasons.append(f"Low P/E ratio ({result.get('pe_ratio', 'N/A')})")
        if result['meets_52week_low_criteria']:
            reasons.append(f"Near 52-week low ({result.get('pct_above_low', 'N/A')}%)")
        if result['is_fallen_ipo']:
            reasons.append(f"Fallen IPO ({result.get('pct_off_high', 'N/A')}% off high)")
        if result['is_cash_rich_biotech']:
            reasons.append(f"Cash-rich ({result.get('cash_to_mc_ratio', 'N/A')}x cash/MC)")
        
        result['reason'] = ", ".join(reasons) if reasons else "Multiple criteria"
        
        # Get additional stock information directly from FMP
        try:
            company_data = fmp_provider.get_company_overview(symbol)
            if company_data:
                result['company_name'] = company_data.get('Name', symbol)
                result['sector'] = company_data.get('Sector', 'Unknown')
                result['market_cap'] = company_data.get('MarketCapitalization', 0)
                
                # Get current price
                price_data = fmp_provider.get_historical_prices(symbol, period="5d")
                if symbol in price_data and not price_data[symbol].empty:
                    result['current_price'] = price_data[symbol]['Close'].iloc[-1]
            else:
                result['company_name'] = symbol
        except Exception as e:
            logger.error(f"Error getting info for {symbol}: {e}")
            result['company_name'] = symbol
        
        results.append(result)
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by score (highest first)
        df = df.sort_values('score', ascending=False)
        return df
    else:
        return pd.DataFrame()

# For backward compatibility
combine_screeners = screen_for_combined

def save_screener_results(df, filename):
    """
    Save screener results to CSV file
    
    Args:
        df (DataFrame): DataFrame with screener results
        filename (str): Filename to save to
    """
    if df is None or df.empty:
        logger.warning(f"No data to save for {filename}")
        return
    
    filepath = os.path.join(config.RESULTS_DIR, filename)
    df.to_csv(filepath, index=False)
    logger.info(f"Saved screener results to {filepath}")

if __name__ == "__main__":
    logger.info("Testing screeners module with new architecture...")
    
    # Check if market is in correction
    in_correction, status = is_market_in_correction()
    logger.info(f"Market status: {status}")
    
    # Test various screeners
    logger.info("Testing book value screener...")
    book_value_stocks = screen_for_price_to_book(universe_df=config.UNIVERSES["SP500"])
    if not book_value_stocks.empty:
        logger.info(f"Found {len(book_value_stocks)} stocks trading near book value")
        save_screener_results(book_value_stocks, "book_value_stocks.csv")
    
    logger.info("Testing PE ratio screener...")
    low_pe_stocks = screen_for_pe_ratio(universe_df=config.UNIVERSES["SP500"])
    if not low_pe_stocks.empty:
        logger.info(f"Found {len(low_pe_stocks)} stocks with low P/E ratios")
        save_screener_results(low_pe_stocks, "low_pe_stocks.csv")
    
    logger.info("Testing 52-week low screener...")
    lows_52week_stocks = screen_for_52_week_lows(universe_df=config.UNIVERSES["SP500"])
    if not lows_52week_stocks.empty:
        logger.info(f"Found {len(lows_52week_stocks)} stocks near 52-week lows")
        save_screener_results(lows_52week_stocks, "52week_low_stocks.csv")
    
    logger.info("Testing fallen IPO screener...")
    fallen_ipos = screen_for_fallen_ipos(universe_df=get_stock_universe(config.UNIVERSES["NASDAQ100"]))
    if not fallen_ipos.empty:
        logger.info(f"Found {len(fallen_ipos)} fallen IPOs")
        save_screener_results(fallen_ipos, "fallen_ipos.csv")
    
    logger.info("Testing cash-rich biotech screener...")
    cash_rich_biotech = screen_for_cash_rich_biotech(universe_df=get_stock_universe(config.UNIVERSES["SP500"]))
    if not cash_rich_biotech.empty:
        logger.info(f"Found {len(cash_rich_biotech)} cash-rich biotech stocks")
        save_screener_results(cash_rich_biotech, "cash_rich_biotech.csv")
    
    logger.info("Testing sector correction screener...")
    sector_corrections = screen_for_sector_corrections(universe_df=get_stock_universe(config.UNIVERSES["SP500"]))
    if not sector_corrections.empty:
        unique_sectors = len(sector_corrections['sector'].unique()) if 'sector' in sector_corrections.columns else 0
        logger.info(f"Found {len(sector_corrections)} stocks in {unique_sectors} sectors in correction")
        save_screener_results(sector_corrections, "sector_corrections.csv")
    
    logger.info("Testing combined screener...")
    combined_results = screen_for_combined(universe_df=config.UNIVERSES["SP500"])
    if not combined_results.empty:
        logger.info(f"Found {len(combined_results)} stocks in combined screener")
        logger.info(f"Top 5 stocks by score: {combined_results.head(5)['symbol'].tolist()}")
        save_screener_results(combined_results, "combined_results.csv")
    
    logger.info("Screener tests complete")
