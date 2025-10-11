"""
Quality Screener module.
Screens for high-quality companies based on financial strength metrics.
Research basis: Warren Buffett's quality investing principles and Piotroski F-Score methodology.
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Evaluates financial strength using a 10-point system covering profitability, debt levels, and operational efficiency. Higher scores indicate stronger, more sustainable businesses."


class QualityScreener(BaseScreener):
    """Screener for high-quality companies based on financial strength metrics."""
    
    def __init__(self, min_quality_score=None):
        super().__init__()
        self.min_quality_score = min_quality_score or getattr(config.ScreeningThresholds, 'MIN_QUALITY_SCORE', 6.0)
    
    def get_strategy_name(self):
        return "Quality Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def calculate_score(self, data):
        """
        Calculate quality score (0-10 points) based on financial strength metrics.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            float: Quality score (0-10) or None if insufficient data
        """
        overview = data.get('overview', data)  # Handle both wrapped and direct data
        
        # Extract key financial metrics (using available fields from FMP API)
        roe = self.safe_percentage(overview.get('ReturnOnEquityTTM'))
        debt_to_equity = self.safe_float(overview.get('DebtToEquityRatio'))
        profit_margin = self.safe_percentage(overview.get('ProfitMargin'))
        operating_margin = self.safe_percentage(overview.get('OperatingMarginTTM'))
        ev_ebitda = self.safe_float(overview.get('EVToEBITDA'))
        
        # Need at least 3 metrics to calculate meaningful score
        available_metrics = sum(1 for x in [roe, debt_to_equity, profit_margin, operating_margin, ev_ebitda] if x is not None)
        if available_metrics < 3:
            return None
        
        score = 0
        
        # ROE Analysis (0-3 points)
        if roe is not None:
            if roe > 0.15:  # 15% ROE
                score += 3
            elif roe > 0.10:  # 10% ROE
                score += 1
        
        # Debt-to-Equity Analysis (0-2 points) 
        if debt_to_equity is not None:
            if debt_to_equity < 0.5:
                score += 2
            elif debt_to_equity < 1.0:
                score += 1
        
        # Profit Margin Analysis (0-2 points)
        if profit_margin is not None:
            if profit_margin > 0.20:  # 20% profit margin
                score += 2
            elif profit_margin > 0.10:  # 10% profit margin
                score += 1
        
        # Operating Margin Analysis (0-2 points)
        if operating_margin is not None:
            if operating_margin > 0.15:  # 15% operating margin
                score += 2
            elif operating_margin > 0.10:  # 10% operating margin
                score += 1
        
        # EV/EBITDA Valuation (0-1 point) - Lower is better
        if ev_ebitda is not None:
            if ev_ebitda < 10:  # Attractive valuation
                score += 1
        
        return min(score, 10)  # Cap at 10 points
    
    def meets_threshold(self, score):
        """
        Check if quality score meets minimum threshold.
        
        Args:
            score (float): Quality score
            
        Returns:
            bool: True if score meets minimum quality threshold
        """
        return score is not None and score >= self.min_quality_score
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to quality screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Stock data dictionary
            current_price (float): Current stock price
            
        Returns:
            dict: Additional quality metrics
        """
        overview = data.get('overview', data)
        
        return {
            'roe': self.safe_percentage(overview.get('ReturnOnEquityTTM')),
            'debt_to_equity': self.safe_float(overview.get('DebtToEquityRatio')),
            'profit_margin': self.safe_percentage(overview.get('ProfitMargin')),
            'operating_margin': self.safe_percentage(overview.get('OperatingMarginTTM')),
            'ev_ebitda': self.safe_float(overview.get('EVToEBITDA')),
            'pe_ratio': self.safe_float(overview.get('PERatio'))
        }
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): Quality score
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"High quality fundamentals (Score: {score:.1f}/10)"
        else:
            return f"Quality score: {score:.1f}/10"
    
    def sort_results(self, df):
        """Sort results by quality score (highest first)."""
        return df.sort_values('score', ascending=False)
