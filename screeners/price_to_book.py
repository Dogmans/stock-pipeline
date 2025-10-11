"""
Price to Book Ratio Screener module.
Screens for stocks trading below or near book value.
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Finds stocks trading near or below their book value (tangible assets minus liabilities). Values below 1.0 suggest the stock trades for less than its liquidation value."


class PriceToBookScreener(BaseScreener):
    """Screener for stocks with low Price-to-Book ratios."""
    
    def __init__(self, max_pb_ratio=None):
        super().__init__()
        self.max_pb_ratio = max_pb_ratio or config.ScreeningThresholds.MAX_PRICE_TO_BOOK_RATIO
    
    def get_strategy_name(self):
        return "Price-to-Book Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def calculate_score(self, data):
        """
        Calculate P/B ratio score. Lower P/B ratios get better scores.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            float: P/B ratio (or None if invalid)
        """
        pb_ratio = data.get('PriceToBookRatio')
        
        if pb_ratio is None or pb_ratio == '':
            return None
        
        pb_ratio = self.safe_float(pb_ratio)
        
        # Handle invalid or extremely small P/B ratios
        if pb_ratio is None or pb_ratio <= 0 or pb_ratio < 0.01:
            return None
        
        return pb_ratio
    
    def meets_threshold(self, score):
        """
        Check if P/B ratio meets the screening threshold.
        
        Args:
            score (float): P/B ratio
            
        Returns:
            bool: True if P/B ratio is below maximum threshold
        """
        return score is not None and score <= self.max_pb_ratio
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to P/B screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Company data from providers
            current_price (float): Current stock price
            
        Returns:
            dict: Additional data fields
        """
        additional = {}
        
        # Calculate book value per share if we have valid data
        pb_ratio = self.safe_float(data.get('PriceToBookRatio'))
        if pb_ratio and pb_ratio > 0 and current_price:
            additional['book_value_per_share'] = current_price / pb_ratio
        
        # Rename score to price_to_book for compatibility
        if pb_ratio:
            additional['price_to_book'] = pb_ratio
        
        return additional
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): P/B ratio
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"Low price to book ratio (P/B = {score:.2f})"
        else:
            return f"Price to book ratio: P/B = {score:.2f}"
    
    def sort_results(self, df):
        """Sort results by P/B ratio (lowest first)."""
        return df.sort_values('score')


def screen_for_price_to_book(universe_df, max_pb_ratio=None):
    """
    Legacy function for backward compatibility.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        max_pb_ratio (float): Maximum price-to-book ratio to include
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    screener = PriceToBookScreener(max_pb_ratio=max_pb_ratio)
    return screener.screen_stocks(universe_df)
