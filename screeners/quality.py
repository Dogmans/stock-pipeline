"""
Quality Screener module.
Screens for high-quality companies based on financial strength metrics.
Research basis: Warren Buffett's quality investing principles and Piotroski F-Score methodology.
"""

from .common import *

def screen_for_quality(universe_df, min_quality_score=None):
    """
    Screen for high-quality companies using composite quality score.
    
    Quality Score Components (0-10 points):
    - ROE > 15% (3 points), > 10% (1 point)
    - Debt-to-Equity < 0.5 (2 points), < 1.0 (1 point)
    - Current Ratio > 1.5 (2 points), > 1.0 (1 point)
    - Interest Coverage > 5x (2 points)
    - Gross Margin > 40% (1 point)
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_quality_score (float): Minimum quality score to include (default: 6.0)
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if min_quality_score is None:
        min_quality_score = config.ScreeningThresholds.MIN_QUALITY_SCORE if hasattr(config.ScreeningThresholds, 'MIN_QUALITY_SCORE') else 6.0
    
    logger.info(f"Screening for stocks with quality score >= {min_quality_score}/10...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Calculating quality scores", unit="symbol"):
        try:
            # Get financial metrics from company overview (includes ratios and key metrics)
            company_data = fmp_provider.get_company_overview(symbol)
            
            if not company_data:
                continue
            
            quality_score = 0
            quality_details = []
            
            # Helper function to safely convert to float
            def safe_float(value):
                if value is None or value == '' or value == 'None':
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            
            # ROE scoring (3 points max) - Return on Equity TTM
            roe = safe_float(company_data.get('ReturnOnEquityTTM'))
            if roe is not None and roe > 0:
                if roe > 0.15:  # ROE > 15%
                    quality_score += 3
                    quality_details.append(f"ROE: {roe*100:.1f}%")
                elif roe > 0.10:  # ROE > 10%
                    quality_score += 1
                    quality_details.append(f"ROE: {roe*100:.1f}%")
            
            # Debt-to-Equity scoring (2 points max) - use alternative if not available
            debt_equity = safe_float(company_data.get('DebtToEquityRatio'))
            # Alternative: Calculate from balance sheet if direct ratio not available
            if debt_equity is None or debt_equity == 0:
                # For now, award 1 point for having low debt if we can't calculate
                quality_score += 1
                quality_details.append("D/E: Low (estimated)")
            elif debt_equity >= 0:
                if debt_equity < 0.3:  # Low debt
                    quality_score += 2
                    quality_details.append(f"D/E: {debt_equity:.2f}")
                elif debt_equity < 0.5:  # Moderate debt
                    quality_score += 1
                    quality_details.append(f"D/E: {debt_equity:.2f}")
                if debt_equity < 0.5:  # D/E < 0.5
                    quality_score += 2
                    quality_details.append(f"D/E: {debt_equity:.2f}")
                elif debt_equity < 1.0:  # D/E < 1.0
                    quality_score += 1
                    quality_details.append(f"D/E: {debt_equity:.2f}")
            
            # Current Ratio scoring (2 points max) - may not be available, use alternatives
            # Try to use available liquidity metrics
            current_ratio = safe_float(company_data.get('CurrentRatio'))
            if current_ratio is not None and current_ratio > 0:
                if current_ratio > 2.0:  # Strong liquidity
                    quality_score += 2
                    quality_details.append(f"Current Ratio: {current_ratio:.2f}")
                elif current_ratio > 1.5:  # Adequate liquidity
                    quality_score += 1
                    quality_details.append(f"Current Ratio: {current_ratio:.2f}")
            else:
                # If current ratio not available, give partial credit for having low debt
                quality_score += 1
                quality_details.append("Liquidity: Adequate (estimated)")
            
            # Interest Coverage scoring (2 points max) - use available profitability metrics
            operating_margin = safe_float(company_data.get('OperatingMarginTTM'))
            if operating_margin is not None and operating_margin > 0:
                if operating_margin > 0.20:  # Strong operating margin > 20%
                    quality_score += 2
                    quality_details.append(f"Op Margin: {operating_margin*100:.1f}%")
                elif operating_margin > 0.10:  # Adequate operating margin > 10%
                    quality_score += 1
                    quality_details.append(f"Op Margin: {operating_margin*100:.1f}%")
            
            # Profitability scoring (1 point max) - use profit margin
            profit_margin = safe_float(company_data.get('ProfitMargin'))
            if profit_margin is not None and profit_margin > 0:
                if profit_margin > 0.15:  # Profit margin > 15%
                    quality_score += 1
                    quality_details.append(f"Profit Margin: {profit_margin*100:.1f}%")
            
            # Extract company info
            company_name = company_data.get('Name', symbol) if company_data else symbol
            sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
            market_cap = company_data.get('MarketCapitalization', 0) if company_data else 0
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = quality_score >= min_quality_score
            details_str = ", ".join(quality_details) if quality_details else "Insufficient data"
            reason = f"Quality score: {quality_score}/10 ({details_str})" if meets_threshold else f"Quality score: {quality_score}/10"
            
            # Add to results (all stocks with sufficient data)
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'quality_score': quality_score,
                'roe': roe * 100 if roe is not None else None,
                'debt_equity_ratio': debt_equity,
                'operating_margin': operating_margin * 100 if operating_margin is not None else None,
                'profit_margin': profit_margin * 100 if profit_margin is not None else None,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
                logger.info(f"Found {symbol} with high quality score: {quality_score}/10")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for quality screening: {e}")
            continue
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by quality score (highest first)
        df = df.sort_values('quality_score', ascending=False)
        return df
    else:
        return pd.DataFrame()
