"""
P/E Ratio Screener module.
Screens for stocks with low Price to Earnings ratios.
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Identifies undervalued stocks trading at low price-to-earnings ratios. Lower P/E ratios may indicate better value opportunities, though context matters by sector and growth expectations."


class PERatioScreener(BaseScreener):
    """Screener for stocks with low P/E ratios."""
    
    def __init__(self, max_pe=None):
        super().__init__()
        self.max_pe = max_pe or config.ScreeningThresholds.MAX_PE_RATIO
    
    def get_strategy_name(self):
        return "P/E Ratio Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def calculate_score(self, data):
        """
        Calculate P/E ratio score. Lower P/E ratios get better scores.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            float: P/E ratio (or None if invalid)
        """
        pe_ratio = data.get('PERatio')
        
        if pe_ratio is None or pe_ratio == '':
            return None
        
        pe_ratio = self.safe_float(pe_ratio)
        
        # Handle negative or zero PE ratios - typically excluded
        if pe_ratio is None or pe_ratio <= 0:
            return None
        
        return pe_ratio
    
    def meets_threshold(self, score):
        """
        Check if P/E ratio meets the screening threshold.
        
        Args:
            score (float): P/E ratio
            
        Returns:
            bool: True if P/E ratio is below maximum threshold
        """
        return score is not None and score <= self.max_pe
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to P/E screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Company data from providers
            current_price (float): Current stock price
            
        Returns:
            dict: Additional data fields
        """
        additional = {}
        
        # Calculate forward PE if available
        eps = data.get('EPS')
        if eps and eps != '':
            eps_float = self.safe_float(eps)
            if eps_float and eps_float > 0 and current_price:
                additional['forward_pe'] = current_price / eps_float
        
        return additional
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): P/E ratio
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"Low P/E ratio (P/E = {score:.2f})"
        else:
            return f"P/E ratio: {score:.2f}"
    
    def sort_results(self, df):
        """Sort results by P/E ratio (lowest first)."""
        return df.sort_values('score')


def screen_for_pe_ratio(universe_df, max_pe=None):
    """
    Legacy function for backward compatibility.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        max_pe (float): Maximum P/E ratio to include
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    screener = PERatioScreener(max_pe=max_pe)
    return screener.screen_stocks(universe_df)
