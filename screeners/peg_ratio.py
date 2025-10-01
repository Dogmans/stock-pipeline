"""
PEG Ratio Screener module.
Screens for stocks with low Price/Earnings-to-Growth (PEG) ratios.
"""

from .common import *

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
        from universe import get_stock_universe
        universe_df = get_stock_universe()
    
    # Import providers here to avoid circular imports
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
            if income_stmt is not None and len(income_stmt) >= 5:  # Need at least 5 quarters
                try:
                    # Calculate YoY EPS growth
                    if 'eps' in income_stmt.columns:
                        current_eps = income_stmt['eps'].iloc[0]
                        year_ago_eps = income_stmt['eps'].iloc[4]
                        
                        # Only calculate growth if previous EPS was positive
                        # (negative to positive is infinite growth and skews results)
                        if year_ago_eps > 0 and current_eps > 0:
                            eps_yoy_growth = ((current_eps / year_ago_eps) - 1) * 100
                            growth_rate = eps_yoy_growth
                            growth_type = "EPS YoY"
                except (IndexError, KeyError, TypeError, ZeroDivisionError):
                    pass
            
            # Fall back to company_data growth rates if quarterly calculation failed
            if growth_rate is None:
                if eps_growth is not None and eps_growth != '' and not np.isnan(float(eps_growth)) and float(eps_growth) > 0:
                    # Don't multiply by 100 - assume it's already in percentage format
                    growth_rate = float(eps_growth)
                    growth_type = "EPS Growth"
                elif revenue_growth is not None and revenue_growth != '' and not np.isnan(float(revenue_growth)) and float(revenue_growth) > 0:
                    # Don't multiply by 100 - assume it's already in percentage format
                    growth_rate = float(revenue_growth)
                    growth_type = "Revenue Growth"
            
            # Skip if growth rate is not available, zero/negative, or unrealistically high
            if growth_rate is None or growth_rate <= 0 or growth_rate > 100:  # Cap at 100% growth
                continue
            
            # Calculate PEG ratio
            peg_ratio = pe_ratio / growth_rate
            
            # All stocks are included for ranking, but mark whether they meet the thresholds
            meets_growth_threshold = growth_rate >= min_growth
            meets_peg_threshold = peg_ratio <= max_peg_ratio
            meets_threshold = meets_growth_threshold and meets_peg_threshold
            
            # Get other relevant company information
            company_name = company_data.get('Name', symbol)
            sector = company_data.get('Sector', 'Unknown')
            market_cap = company_data.get('MarketCapitalization', 0)
            
            # Format the reason string - different versions based on whether thresholds are met
            if meets_threshold:
                reason = f"PEG: {peg_ratio:.2f} (P/E: {pe_ratio:.2f}, Growth: {growth_rate:.1f}% {growth_type})"
            else:
                reason = f"PEG ratio: {peg_ratio:.2f}"
            
            # Add stock to results
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'pe_ratio': pe_ratio,
                'growth_rate': growth_rate,
                'growth_type': growth_type,
                'peg_ratio': peg_ratio,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
        except Exception as e:
            logger.error(f"Error processing {symbol} for PEG ratio screening: {e}")
            continue
    
    # Convert results to DataFrame
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    
    # Sort by PEG ratio (ascending)
    if not result_df.empty:
        result_df = result_df.sort_values('peg_ratio')
    
    logger.info(f"Found {len(result_df)} stocks with favorable PEG ratios")
    return result_df
