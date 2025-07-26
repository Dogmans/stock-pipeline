"""
Free Cash Flow Yield Screener module.
Screens for stocks with high free cash flow yield relative to market capitalization.
Research basis: Joel Greenblatt's "Magic Formula" and FCF yield as predictor of long-term returns.
"""

from .common import *

def screen_for_free_cash_flow_yield(universe_df, min_fcf_yield=None):
    """
    Screen for stocks with high free cash flow yield.
    
    FCF Yield is calculated as:
    FCF Yield = Free Cash Flow (TTM) / Market Capitalization * 100
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_fcf_yield (float): Minimum FCF yield to include (default: 8.0%)
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if min_fcf_yield is None:
        min_fcf_yield = config.ScreeningThresholds.MIN_FCF_YIELD if hasattr(config.ScreeningThresholds, 'MIN_FCF_YIELD') else 8.0
    
    logger.info(f"Screening for stocks with FCF yield >= {min_fcf_yield}%...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Calculating FCF yields", unit="symbol"):
        try:
            # Get cash flow statement and company overview
            cash_flow = fmp_provider.get_cash_flow(symbol)
            company_data = fmp_provider.get_company_overview(symbol)
            
            if cash_flow is None or not company_data or cash_flow.empty:
                continue
            
            # Get free cash flow (TTM) - use the most recent entry
            latest_cash_flow = cash_flow.iloc[0]  # Most recent year
            free_cash_flow = latest_cash_flow.get('freeCashflow')  # Note: lowercase 'f'
            market_cap = company_data.get('MarketCapitalization')
            
            if not free_cash_flow or not market_cap or market_cap <= 0:
                continue
            
            # Calculate FCF Yield
            fcf_yield = (free_cash_flow / market_cap) * 100
            
            # Only consider stocks with positive free cash flow
            if free_cash_flow <= 0:
                continue
            
            # Extract company info
            company_name = company_data.get('Name', symbol)
            sector = company_data.get('Sector', 'Unknown')
            current_price = company_data.get('Price', 0)
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = fcf_yield >= min_fcf_yield
            reason = f"FCF Yield: {fcf_yield:.1f}% (FCF: ${free_cash_flow/1e9:.1f}B)" if meets_threshold else f"FCF Yield: {fcf_yield:.1f}%"
            
            # Add to results (all stocks with positive FCF)
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                'fcf_yield': fcf_yield,
                'free_cash_flow': free_cash_flow,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
                logger.info(f"Found {symbol} with high FCF yield: {fcf_yield:.1f}%")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for FCF yield screening: {e}")
            continue
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by FCF yield (highest first)
        df = df.sort_values('fcf_yield', ascending=False)
        return df
    else:
        return pd.DataFrame()
