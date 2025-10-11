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
from .base_screener import BaseScreener
import config

logger = logging.getLogger(__name__)


class EnhancedQualityScreener(BaseScreener):
    """Enhanced quality screening with 0-100 point granular scoring system across four dimensions."""
    
    def get_strategy_name(self) -> str:
        """Return the strategy name for this screener."""
        return "Enhanced Quality"
    
    def get_strategy_description(self) -> str:
        """Return the strategy description for this screener."""
        return ("Advanced quality analysis with 0-100 granular scoring across four dimensions: "
                "ROE (25 pts), Profitability (25 pts), Financial Strength (25 pts), and Growth Quality (25 pts). "
                "Higher scores indicate superior financial quality.")
    
    def calculate_score(self, data: dict) -> float:
        """
        Calculate enhanced quality score (0-100 points) across four dimensions.
        
        Args:
            data: Dictionary containing all relevant data for the stock
            
        Returns:
            Enhanced quality score (0-100)
        """
        # Extract symbol and company data from the data dict
        symbol = data.get('symbol', 'Unknown')
        company_data = data
        
        if not company_data:
            return 0.0
            
        # Helper function to safely convert to float
        def safe_float(value):
            if value is None or value == '' or value == 'None':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Initialize scoring components
        roe_score = 0
        profitability_score = 0
        financial_strength_score = 0
        growth_quality_score = 0
        
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
        elif debt_equity is None:
            # Give partial credit if D/E ratio not available
            debt_score = 3
        
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
        else:
            # Give minimal credit if current ratio not available
            liquidity_score = 1
        
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
        
        # Dividend sustainability (0-4 points)
        dividend_yield = safe_float(company_data.get('DividendYield'))
        payout_ratio = safe_float(company_data.get('PayoutRatio'))
        dividend_score = 0
        
        if dividend_yield is not None and dividend_yield > 0:
            if payout_ratio is not None and 0 < payout_ratio < 0.6:  # Sustainable payout
                dividend_score = 4
            elif payout_ratio is not None and 0.6 <= payout_ratio < 0.8:  # Moderate payout
                dividend_score = 2
            else:
                dividend_score = 1  # Has dividend but unknown sustainability
        
        growth_quality_score = revenue_score + eps_score + roa_score + dividend_score
        
        # ===== CALCULATE TOTAL ENHANCED QUALITY SCORE =====
        total_quality_score = roe_score + profitability_score + financial_strength_score + growth_quality_score
        
        return total_quality_score
    
    def meets_threshold(self, score: float) -> bool:
        """
        Check if stock meets enhanced quality threshold.
        
        Args:
            score: Calculated enhanced quality score
            
        Returns:
            True if score meets minimum threshold
        """
        min_score = getattr(config.ScreeningThresholds, 'MIN_ENHANCED_QUALITY_SCORE', 50.0)
        return score is not None and score >= min_score
    
    def get_detailed_metrics(self, symbol: str, company_data: dict, score: float) -> dict:
        """Get detailed enhanced quality metrics for a stock."""
        if not company_data:
            return {}
        
        # Helper function to safely convert to float
        def safe_float(value):
            if value is None or value == '' or value == 'None':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Extract key metrics
        roe = safe_float(company_data.get('ReturnOnEquityTTM'))
        operating_margin = safe_float(company_data.get('OperatingMarginTTM'))
        profit_margin = safe_float(company_data.get('ProfitMargin'))
        debt_equity = safe_float(company_data.get('DebtToEquityRatio'))
        current_ratio = safe_float(company_data.get('CurrentRatio'))
        revenue_growth = safe_float(company_data.get('RevenueGrowthTTM'))
        
        return {
            'enhanced_quality_score': score,
            'roe_ttm': roe * 100 if roe is not None else None,
            'operating_margin': operating_margin * 100 if operating_margin is not None else None,
            'profit_margin': profit_margin * 100 if profit_margin is not None else None,
            'debt_equity_ratio': debt_equity,
            'current_ratio': current_ratio,
            'revenue_growth': revenue_growth * 100 if revenue_growth is not None else None
        }


