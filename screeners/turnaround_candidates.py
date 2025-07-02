"""
Turnaround Candidates Screener module.
Screens for companies showing signs of financial turnaround or improvement.
"""

from .common import *

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
                
            # Determine if this stock meets the threshold
            meets_threshold = turnaround_score >= 5
            
            # Create detailed reason text for reporting
            has_true_turnaround = true_eps_turnaround or revenue_turnaround
            primary_factor = factors[0] if factors else "multiple factors"
            
            # Different text for meets threshold vs not
            if meets_threshold:
                score_text = f"Score: {turnaround_score} - {', '.join(factors)}"
            else:
                score_text = f"Turnaround score: {turnaround_score}" + (f" - {', '.join(factors)}" if factors else "")
              
            # Add EPS transition text
            if true_eps_turnaround:
                eps_trend_text = "Negative-to-Positive EPS"
            elif strong_eps_improvement:
                eps_trend_text = f"Strong EPS growth: {eps_yoy_change:.1f}%" if eps_yoy_change else "Strong EPS growth"
            else:
                eps_trend_text = "Improving EPS" if eps_yoy_change and eps_yoy_change > 0 else "Stable EPS"
            
            # Add all stocks to results, even if they don't meet threshold
            results.append({
                'symbol': symbol,
                'company_name': company_data.get('Name', symbol),
                'sector': company_data.get('Sector', 'Unknown'),
                'turnaround_score': turnaround_score,
                'true_turnaround': has_true_turnaround,  # Flag for sorting
                'meets_threshold': meets_threshold,
                'eps_trend': eps_trend_text,
                'revenue_trend': ('Recovery' if revenue_turnaround else 
                                'Accelerating' if revenue_reaccelerating else 'Stable'),
                'margins': 'Recovering' if margins_recovering else 'Stable',
                'balance_sheet': ('Strengthening' if cash_improvement or debt_reduction else 'Stable'),
                'latest_eps': eps_values[0] if len(eps_values) > 0 else None,
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
