"""
Momentum Screener module.
Screens for stocks with strong price momentum based on 6-month and 3-month returns.
Research basis: Jegadeesh & Titman (1993) - Returns to Buying Winners and Selling Losers.
"""

from .common import *

def screen_for_momentum(universe_df, min_momentum_score=None, lookback_period="7mo"):
    """
    Screen for stocks with strong price momentum.
    
    Momentum is calculated as:
    Momentum Score = (6-month return * 0.6) + (3-month return * 0.4)
    (Skips most recent month to avoid short-term reversal effects)
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_momentum_score (float): Minimum momentum score to include (default: 15.0)
        lookback_period (str): Period for calculating momentum (default: "7mo")
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if min_momentum_score is None:
        min_momentum_score = config.ScreeningThresholds.MIN_MOMENTUM_SCORE if hasattr(config.ScreeningThresholds, 'MIN_MOMENTUM_SCORE') else 15.0
    
    logger.info(f"Screening for stocks with momentum score >= {min_momentum_score}% over {lookback_period} period...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Calculating momentum", unit="symbol"):
        try:
            # Get historical price data (7 months to skip most recent month)
            price_data = fmp_provider.get_historical_prices(symbol, period=lookback_period)
            
            if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                continue
                
            df = price_data[symbol]
            
            # Need at least 150 days of data for meaningful momentum calculation
            if len(df) < 150:
                continue
                
            # Skip most recent 20 days to avoid short-term reversal effects
            prices = df['Close'].iloc[:-20]
            
            if len(prices) < 130:
                continue
            
            # Calculate 6-month return (ending 1 month ago)
            if len(prices) >= 126:
                six_month_return = (prices.iloc[-1] / prices.iloc[-126] - 1) * 100
            else:
                continue
                
            # Calculate 3-month return (ending 1 month ago)
            if len(prices) >= 63:
                three_month_return = (prices.iloc[-1] / prices.iloc[-63] - 1) * 100
            else:
                continue
            
            # Calculate momentum score (weighted combination)
            momentum_score = (six_month_return * 0.6) + (three_month_return * 0.4)
            
            # Get company overview data for additional info
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Extract company info
            company_name = company_data.get('Name', symbol) if company_data else symbol
            sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
            market_cap = company_data.get('MarketCapitalization', 0) if company_data else 0
            current_price = df['Close'].iloc[-1]
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = momentum_score >= min_momentum_score
            reason = f"High momentum (Score: {momentum_score:.1f}%, 6M: {six_month_return:.1f}%, 3M: {three_month_return:.1f}%)" if meets_threshold else f"Momentum score: {momentum_score:.1f}%"
            
            # Add to results (all stocks with sufficient data)
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                'momentum_score': momentum_score,
                'six_month_return': six_month_return,
                'three_month_return': three_month_return,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
                logger.info(f"Found {symbol} with high momentum: {momentum_score:.1f}%")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for momentum screening: {e}")
            continue
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by momentum score (highest first)
        df = df.sort_values('momentum_score', ascending=False)
        return df
    else:
        return pd.DataFrame()
