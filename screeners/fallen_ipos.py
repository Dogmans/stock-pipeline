"""
Fallen IPOs Screener module.
Screens for recent IPOs that have dropped significantly from their highs.
"""

from .common import *

STRATEGY_DESCRIPTION = "Targets IPO stocks that have declined significantly but may be stabilizing. Looks for companies that have moved past initial volatility and are approaching sustainable operations."

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
            
            # Check if it meets the threshold
            meets_threshold = pct_off_high >= min_pct_off_high
            
            # Create reason text based on whether it meets threshold
            reason = f"Fallen IPO ({pct_off_high:.2f}% off high)" if meets_threshold else f"IPO status: {pct_off_high:.2f}% off high"
                    
            # Add to results - include all stocks with valid price data
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
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
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
