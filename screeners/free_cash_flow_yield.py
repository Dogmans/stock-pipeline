"""
Free Cash Flow Yield Screener module.
Screens for stocks with high free cash flow yield relative to market capitalization.
Research basis: Joel Greenblatt's "Magic Formula" and FCF yield as predictor of long-term returns.
"""

from .common import *

STRATEGY_DESCRIPTION = "Screens for stocks with high free cash flow relative to market capitalization. Higher FCF yields may indicate better value and cash-generating ability."

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
            # Get company data which includes pre-calculated freeCashFlowYield
            company_data = fmp_provider.get_company_overview(symbol)
            
            if not company_data:
                continue
            
            # Use API's pre-calculated FCF yield (in decimal format)
            fcf_yield_decimal = company_data.get('freeCashFlowYield')
            
            if fcf_yield_decimal is None or pd.isna(fcf_yield_decimal):
                # Skip stocks without FCF yield data
                continue
                
            # Convert from decimal to percentage (0.031 -> 3.1%)
            fcf_yield = float(fcf_yield_decimal) * 100
            
            # Only consider stocks with positive FCF yield
            if fcf_yield <= 0:
                continue
            
            # Get market cap for display purposes
            market_cap = company_data.get('MarketCapitalization')
            
            # Extract company info
            company_name = company_data.get('Name', symbol)
            sector = company_data.get('Sector', 'Unknown')
            current_price = company_data.get('Price', 0)
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = fcf_yield >= min_fcf_yield
            reason = f"FCF Yield: {fcf_yield:.1f}%" + (" (Strong)" if meets_threshold else "")
            
            # Add to results (all stocks with positive FCF yield)
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                'fcf_yield': fcf_yield,
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
