"""
52-Week Lows Screener module.
Screens for stocks trading near their 52-week low price.
"""

from .common import *
from market_data import is_market_in_correction

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
            
            # Get company overview and additional data regardless of threshold
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
            
            # Check if the stock meets the criteria
            meets_threshold = pct_above_low <= max_pct_above_low
            if min_pct_off_high is not None:
                meets_threshold = meets_threshold and (pct_off_high >= min_pct_off_high)
            
            # Create reason text based on whether it meets threshold
            reason = f"Near 52-week low ({pct_above_low:.2f}% above low)" if meets_threshold else f"52-week low status: {pct_above_low:.2f}% above low"
            
            # Add to results - include all stocks with valid price data
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
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
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
