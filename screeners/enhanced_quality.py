"""
Enhanced Quality Screener
Provides granular 0-100 point scoring system across four quality dimensions:
1. ROE Analysis (0-25 points)
2. Profitability Analysis (0-25 points) 
3. Financial Strength (0-25 points)
4. Growth Quality (0-25 points)

This enhanced screener provides much better differentiation between high-quality stocks
compared to the original binary scoring system.
"""

import pandas as pd
import logging
from tqdm import tqdm
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from .common import *

STRATEGY_DESCRIPTION = "Advanced quality analysis with 0-100 granular scoring across four dimensions: ROE (25 pts), Profitability (25 pts), Financial Strength (25 pts), and Growth Quality (25 pts). Higher scores indicate superior financial quality."

logger = logging.getLogger(__name__)

def screen_for_enhanced_quality(universe_df, min_enhanced_quality_score=None):
    """
    Main enhanced quality screening function that matches the expected screener interface.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_enhanced_quality_score (float): Minimum enhanced quality score for meets_threshold flag (default: from config)
        
    Returns:
        DataFrame: All stocks sorted by enhanced quality score (highest first)
    """
    if min_enhanced_quality_score is None:
        min_enhanced_quality_score = config.ScreeningThresholds.MIN_ENHANCED_QUALITY_SCORE if hasattr(config.ScreeningThresholds, 'MIN_ENHANCED_QUALITY_SCORE') else 50.0
    
    logger.info(f"Screening for enhanced quality scores (threshold: {min_enhanced_quality_score}/100 for meets_threshold flag)...")
    
    # Extract symbols from universe
    symbols = universe_df['symbol'].tolist()
    
    # Run the enhanced quality analysis
    return enhanced_quality_screener(symbols, min_quality_score=min_enhanced_quality_score)

def enhanced_quality_screener(symbols, min_quality_score=50.0):
    """
    Enhanced quality screening with 0-100 point granular scoring system.
    Returns all stocks sorted by score, with meets_threshold flag for reference.
    
    Args:
        symbols: List of stock symbols to analyze
        min_quality_score: Minimum quality score for meets_threshold flag (0-100)
    
    Returns:
        DataFrame with enhanced quality scores and detailed metrics, sorted by score (highest first)
    """
    logger.info(f"Running enhanced quality screening on {len(symbols)} symbols (threshold: {min_quality_score}/100 for meets_threshold flag)")
    
    provider = FinancialModelingPrepProvider()
    results = []
    
    for symbol in tqdm(symbols, desc="Enhanced quality screening", unit="symbol"):
        try:
            # Get comprehensive company data
            company_data = provider.get_company_overview(symbol)
            
            if not company_data:
                continue
            
            # Initialize scoring components
            roe_score = 0
            profitability_score = 0
            financial_strength_score = 0
            growth_quality_score = 0
            quality_details = []
            
            # Helper function to safely convert to float
            def safe_float(value):
                if value is None or value == '' or value == 'None':
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            
            # ===== ROE ANALYSIS (0-25 points) =====
            roe = safe_float(company_data.get('ReturnOnEquityTTM'))
            if roe is not None and roe > 0:
                if roe >= 0.30:      # ROE >= 30% (exceptional)
                    roe_score = 25
                elif roe >= 0.25:    # ROE >= 25% (excellent)
                    roe_score = 22
                elif roe >= 0.20:    # ROE >= 20% (very good)
                    roe_score = 19
                elif roe >= 0.15:    # ROE >= 15% (good)
                    roe_score = 15
                elif roe >= 0.12:    # ROE >= 12% (above average)
                    roe_score = 12
                elif roe >= 0.10:    # ROE >= 10% (average)
                    roe_score = 8
                elif roe >= 0.08:    # ROE >= 8% (below average)
                    roe_score = 5
                elif roe >= 0.05:    # ROE >= 5% (poor)
                    roe_score = 2
                # ROE < 5% gets 0 points
                quality_details.append(f"ROE: {roe*100:.1f}% ({roe_score}pts)")
            
            # ===== PROFITABILITY ANALYSIS (0-25 points) =====
            # Operating margin (0-12 points)
            operating_margin = safe_float(company_data.get('OperatingMarginTTM'))
            op_margin_score = 0
            if operating_margin is not None and operating_margin > 0:
                if operating_margin >= 0.30:     # >= 30%
                    op_margin_score = 12
                elif operating_margin >= 0.25:   # >= 25%
                    op_margin_score = 10
                elif operating_margin >= 0.20:   # >= 20%
                    op_margin_score = 8
                elif operating_margin >= 0.15:   # >= 15%
                    op_margin_score = 6
                elif operating_margin >= 0.10:   # >= 10%
                    op_margin_score = 4
                elif operating_margin >= 0.05:   # >= 5%
                    op_margin_score = 2
                quality_details.append(f"Op Margin: {operating_margin*100:.1f}% ({op_margin_score}pts)")
            
            # Profit margin (0-8 points)
            profit_margin = safe_float(company_data.get('ProfitMargin'))
            profit_margin_score = 0
            if profit_margin is not None and profit_margin > 0:
                if profit_margin >= 0.25:       # >= 25%
                    profit_margin_score = 8
                elif profit_margin >= 0.20:     # >= 20%
                    profit_margin_score = 7
                elif profit_margin >= 0.15:     # >= 15%
                    profit_margin_score = 5
                elif profit_margin >= 0.10:     # >= 10%
                    profit_margin_score = 3
                elif profit_margin >= 0.05:     # >= 5%
                    profit_margin_score = 1
                quality_details.append(f"Profit Margin: {profit_margin*100:.1f}% ({profit_margin_score}pts)")
            
            # Gross margin (0-5 points)
            gross_margin = safe_float(company_data.get('GrossProfitMargin'))
            gross_margin_score = 0
            if gross_margin is not None and gross_margin > 0:
                if gross_margin >= 0.70:        # >= 70%
                    gross_margin_score = 5
                elif gross_margin >= 0.60:      # >= 60%
                    gross_margin_score = 4
                elif gross_margin >= 0.50:      # >= 50%
                    gross_margin_score = 3
                elif gross_margin >= 0.40:      # >= 40%
                    gross_margin_score = 2
                elif gross_margin >= 0.30:      # >= 30%
                    gross_margin_score = 1
                quality_details.append(f"Gross Margin: {gross_margin*100:.1f}% ({gross_margin_score}pts)")
            
            profitability_score = op_margin_score + profit_margin_score + gross_margin_score
            
            # ===== FINANCIAL STRENGTH (0-25 points) =====
            # Debt-to-equity ratio (0-10 points)
            debt_equity = safe_float(company_data.get('DebtToEquityRatio'))
            debt_score = 0
            if debt_equity is not None and debt_equity >= 0:
                if debt_equity <= 0.1:          # <= 0.1 (minimal debt)
                    debt_score = 10
                elif debt_equity <= 0.2:        # <= 0.2 (very low debt)
                    debt_score = 8
                elif debt_equity <= 0.3:        # <= 0.3 (low debt)
                    debt_score = 6
                elif debt_equity <= 0.5:        # <= 0.5 (moderate debt)
                    debt_score = 4
                elif debt_equity <= 0.8:        # <= 0.8 (higher debt)
                    debt_score = 2
                elif debt_equity <= 1.0:        # <= 1.0 (high debt)
                    debt_score = 1
                # > 1.0 gets 0 points
                quality_details.append(f"D/E: {debt_equity:.2f} ({debt_score}pts)")
            elif debt_equity is None:
                # Give partial credit if D/E ratio not available
                debt_score = 3
                quality_details.append(f"D/E: N/A ({debt_score}pts)")
            
            # Current ratio (0-8 points)
            current_ratio = safe_float(company_data.get('CurrentRatio'))
            liquidity_score = 0
            if current_ratio is not None and current_ratio > 0:
                if current_ratio >= 3.0:        # >= 3.0 (excellent liquidity)
                    liquidity_score = 8
                elif current_ratio >= 2.5:      # >= 2.5 (very good)
                    liquidity_score = 7
                elif current_ratio >= 2.0:      # >= 2.0 (good)
                    liquidity_score = 5
                elif current_ratio >= 1.5:      # >= 1.5 (adequate)
                    liquidity_score = 3
                elif current_ratio >= 1.2:      # >= 1.2 (acceptable)
                    liquidity_score = 1
                # < 1.2 gets 0 points
                quality_details.append(f"Current Ratio: {current_ratio:.2f} ({liquidity_score}pts)")
            else:
                # Give minimal credit if current ratio not available
                liquidity_score = 1
                quality_details.append(f"Current Ratio: N/A ({liquidity_score}pts)")
            
            # Quick ratio if available (0-4 points bonus)
            quick_ratio = safe_float(company_data.get('QuickRatio'))
            quick_score = 0
            if quick_ratio is not None and quick_ratio > 0:
                if quick_ratio >= 1.5:          # >= 1.5 (excellent)
                    quick_score = 4
                elif quick_ratio >= 1.2:        # >= 1.2 (good)
                    quick_score = 3
                elif quick_ratio >= 1.0:        # >= 1.0 (adequate)
                    quick_score = 2
                elif quick_ratio >= 0.8:        # >= 0.8 (acceptable)
                    quick_score = 1
                quality_details.append(f"Quick Ratio: {quick_ratio:.2f} ({quick_score}pts)")
            
            # Interest coverage estimate from operating margin (0-3 points)
            interest_coverage_score = 0
            if operating_margin is not None and operating_margin > 0:
                # Higher operating margins suggest better interest coverage
                if operating_margin >= 0.20:    # >= 20% suggests strong coverage
                    interest_coverage_score = 3
                elif operating_margin >= 0.15:  # >= 15% suggests good coverage
                    interest_coverage_score = 2
                elif operating_margin >= 0.10:  # >= 10% suggests adequate coverage
                    interest_coverage_score = 1
            
            financial_strength_score = debt_score + liquidity_score + quick_score + interest_coverage_score
            
            # ===== GROWTH QUALITY (0-25 points) =====
            # Revenue growth consistency (0-8 points)
            revenue_growth = safe_float(company_data.get('RevenueGrowthTTM'))
            revenue_score = 0
            if revenue_growth is not None:
                if revenue_growth >= 0.20:      # >= 20% growth
                    revenue_score = 8
                elif revenue_growth >= 0.15:    # >= 15% growth
                    revenue_score = 6
                elif revenue_growth >= 0.10:    # >= 10% growth
                    revenue_score = 4
                elif revenue_growth >= 0.05:    # >= 5% growth
                    revenue_score = 2
                elif revenue_growth >= 0:       # Positive growth
                    revenue_score = 1
                # Negative growth gets 0 points
                quality_details.append(f"Rev Growth: {revenue_growth*100:.1f}% ({revenue_score}pts)")
            
            # Earnings growth (0-8 points)
            eps_growth = safe_float(company_data.get('EPSGrowth'))
            eps_score = 0
            if eps_growth is not None:
                if eps_growth >= 0.25:          # >= 25% EPS growth
                    eps_score = 8
                elif eps_growth >= 0.20:        # >= 20% EPS growth
                    eps_score = 6
                elif eps_growth >= 0.15:        # >= 15% EPS growth
                    eps_score = 4
                elif eps_growth >= 0.10:        # >= 10% EPS growth
                    eps_score = 2
                elif eps_growth >= 0:           # Positive EPS growth
                    eps_score = 1
                quality_details.append(f"EPS Growth: {eps_growth*100:.1f}% ({eps_score}pts)")
            
            # Return on Assets (0-5 points)
            roa = safe_float(company_data.get('ReturnOnAssetsTTM'))
            roa_score = 0
            if roa is not None and roa > 0:
                if roa >= 0.15:                 # >= 15% ROA
                    roa_score = 5
                elif roa >= 0.12:               # >= 12% ROA
                    roa_score = 4
                elif roa >= 0.08:               # >= 8% ROA
                    roa_score = 3
                elif roa >= 0.05:               # >= 5% ROA
                    roa_score = 2
                elif roa >= 0.02:               # >= 2% ROA
                    roa_score = 1
                quality_details.append(f"ROA: {roa*100:.1f}% ({roa_score}pts)")
            
            # Dividend sustainability (0-4 points)
            dividend_yield = safe_float(company_data.get('DividendYield'))
            payout_ratio = safe_float(company_data.get('PayoutRatio'))
            dividend_score = 0
            
            if dividend_yield is not None and dividend_yield > 0:
                if payout_ratio is not None and 0 < payout_ratio < 0.6:  # Sustainable payout
                    dividend_score = 4
                    quality_details.append(f"Div Yield: {dividend_yield*100:.1f}%, Payout: {payout_ratio*100:.1f}% ({dividend_score}pts)")
                elif payout_ratio is not None and 0.6 <= payout_ratio < 0.8:  # Moderate payout
                    dividend_score = 2
                    quality_details.append(f"Div Yield: {dividend_yield*100:.1f}%, Payout: {payout_ratio*100:.1f}% ({dividend_score}pts)")
                else:
                    dividend_score = 1  # Has dividend but unknown sustainability
                    quality_details.append(f"Div Yield: {dividend_yield*100:.1f}% ({dividend_score}pts)")
            
            growth_quality_score = revenue_score + eps_score + roa_score + dividend_score
            
            # ===== CALCULATE TOTAL ENHANCED QUALITY SCORE =====
            total_quality_score = roe_score + profitability_score + financial_strength_score + growth_quality_score
            
            # Extract company info
            company_name = company_data.get('Name', symbol) if company_data else symbol
            sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
            market_cap = company_data.get('MarketCapitalization', 0) if company_data else 0
            
            # Determine if meets threshold
            meets_threshold = total_quality_score >= min_quality_score
            details_str = ", ".join(quality_details) if quality_details else "Insufficient data"
            
            # Create reason string with component breakdown
            if meets_threshold:
                reason = f"High enhanced quality (Score: {total_quality_score:.0f}/100, ROE:{roe_score}, Prof:{profitability_score}, Fin:{financial_strength_score}, Growth:{growth_quality_score})"
            else:
                reason = f"Enhanced quality score: {total_quality_score:.0f}/100"
            
            # Add to results
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'enhanced_quality_score': total_quality_score,
                'roe_score': roe_score,
                'profitability_score': profitability_score,
                'financial_strength_score': financial_strength_score,
                'growth_quality_score': growth_quality_score,
                'roe_ttm': roe * 100 if roe is not None else None,
                'operating_margin': operating_margin * 100 if operating_margin is not None else None,
                'profit_margin': profit_margin * 100 if profit_margin is not None else None,
                'debt_equity_ratio': debt_equity,
                'current_ratio': current_ratio,
                'revenue_growth': revenue_growth * 100 if revenue_growth is not None else None,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason,
                'quality_details': details_str
            })
            
            if meets_threshold:
                logger.debug(f"Found {symbol} with high enhanced quality score: {total_quality_score:.0f}/100")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for enhanced quality screening: {e}")
            continue
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by enhanced quality score (highest first)
        df = df.sort_values('enhanced_quality_score', ascending=False)
        logger.info(f"Enhanced quality screening completed. Analyzed {len(df)} stocks with data (sorted by score)")
        return df
    else:
        logger.warning("No results returned from enhanced quality screening")
        return pd.DataFrame()

def calculate_enhanced_quality_statistics(df):
    """
    Calculate statistics for enhanced quality scores to help understand distribution.
    
    Args:
        df: DataFrame with enhanced quality results
    
    Returns:
        Dictionary with quality score statistics
    """
    if df.empty:
        return {}
    
    stats = {
        'total_stocks': len(df),
        'mean_score': df['enhanced_quality_score'].mean(),
        'median_score': df['enhanced_quality_score'].median(),
        'std_dev': df['enhanced_quality_score'].std(),
        'min_score': df['enhanced_quality_score'].min(),
        'max_score': df['enhanced_quality_score'].max(),
        'top_10_percent_threshold': df['enhanced_quality_score'].quantile(0.9),
        'top_25_percent_threshold': df['enhanced_quality_score'].quantile(0.75),
        'scores_above_80': len(df[df['enhanced_quality_score'] >= 80]),
        'scores_above_70': len(df[df['enhanced_quality_score'] >= 70]),
        'scores_above_60': len(df[df['enhanced_quality_score'] >= 60]),
        'scores_above_50': len(df[df['enhanced_quality_score'] >= 50]),
    }
    
    return stats
