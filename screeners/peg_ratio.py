"""
PEG Ratio Screener module.
Screens for stocks with low Price/Earnings-to-Growth (PEG) ratios.
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Screens for stocks with attractive Price/Earnings-to-Growth ratios. PEG ratios below 1.0 suggest the stock may be undervalued relative to its growth prospects."


class PEGRatioScreener(BaseScreener):
    """Screener for stocks with low PEG ratios."""
    
    def __init__(self, max_peg_ratio=1.0, min_growth=5.0):
        super().__init__()
        self.max_peg_ratio = max_peg_ratio
        self.min_growth = min_growth
    
    def get_strategy_name(self):
        return "PEG Ratio Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def calculate_score(self, data):
        """
        Calculate PEG ratio score. Lower PEG ratios get better scores.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            float: PEG ratio (or None if invalid)
        """
        # Get P/E ratio
        pe_ratio = data.get('PERatio')
        if pe_ratio is None or pe_ratio == '':
            return None
        
        pe_ratio = self.safe_float(pe_ratio)
        if pe_ratio is None or pe_ratio <= 0:
            return None
        
        # Calculate growth rate using multiple data sources
        growth_rate = self._calculate_growth_rate(data)
        
        if growth_rate is None or growth_rate <= 0 or growth_rate > 100:  # Cap at 100% growth
            return None
        
        # Calculate PEG ratio
        peg_ratio = pe_ratio / growth_rate
        return peg_ratio
    
    def meets_threshold(self, score):
        """
        Check if PEG ratio meets the screening threshold.
        
        Args:
            score (float): PEG ratio
            
        Returns:
            bool: True if PEG ratio is below maximum threshold
        """
        return score is not None and score <= self.max_peg_ratio
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to PEG screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Company data from providers
            current_price (float): Current stock price
            
        Returns:
            dict: Additional data fields
        """
        additional = {}
        
        # Add P/E ratio
        pe_ratio = self.safe_float(data.get('PERatio'))
        if pe_ratio:
            additional['pe_ratio'] = pe_ratio
        
        # Add growth rate and type
        growth_data = self._get_growth_rate_details(data)
        if growth_data:
            additional['growth_rate'] = growth_data['rate']
            additional['growth_type'] = growth_data['type']
        
        return additional
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): PEG ratio
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        # Get additional context from the last processed symbol's data
        # This is a bit of a hack but works for formatting
        if hasattr(self, '_last_pe_ratio') and hasattr(self, '_last_growth_rate') and hasattr(self, '_last_growth_type'):
            if meets_threshold_flag:
                return f"PEG: {score:.2f} (P/E: {self._last_pe_ratio:.2f}, Growth: {self._last_growth_rate:.1f}% {self._last_growth_type})"
            else:
                return f"PEG ratio: {score:.2f}"
        else:
            return f"PEG ratio: {score:.2f}"
    
    def sort_results(self, df):
        """Sort results by PEG ratio (lowest first)."""
        return df.sort_values('score')
    
    def _calculate_growth_rate(self, data):
        """
        Calculate growth rate from multiple data sources.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            float: Growth rate percentage (or None if not available)
        """
        growth_data = self._get_growth_rate_details(data)
        return growth_data['rate'] if growth_data else None
    
    def _get_growth_rate_details(self, data):
        """
        Get growth rate and type from multiple data sources.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            dict: Growth rate details with 'rate' and 'type' keys (or None)
        """
        symbol = data.get('symbol')
        
        # Try quarterly EPS growth calculation first
        growth_result = self._calculate_quarterly_growth(symbol)
        if growth_result:
            return growth_result
        
        # Fall back to company overview growth rates
        eps_growth = data.get('EPSGrowth')
        revenue_growth = data.get('RevenueGrowth')
        
        if eps_growth is not None and eps_growth != '':
            eps_float = self.safe_float(eps_growth)
            if eps_float is not None and eps_float > 0:
                # FMP API returns growth rates in decimal format (0.15 = 15%)
                growth_rate = eps_float * 100
                return {'rate': growth_rate, 'type': 'EPS Growth'}
        
        if revenue_growth is not None and revenue_growth != '':
            rev_float = self.safe_float(revenue_growth)
            if rev_float is not None and rev_float > 0:
                # FMP API returns growth rates in decimal format (0.15 = 15%)
                growth_rate = rev_float * 100
                return {'rate': growth_rate, 'type': 'Revenue Growth'}
        
        return None
    
    def _calculate_quarterly_growth(self, symbol):
        """
        Calculate YoY EPS growth from quarterly data.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Growth rate details with 'rate' and 'type' keys (or None)
        """
        try:
            fmp_provider = data_providers.get_provider("financial_modeling_prep")
            income_stmt = fmp_provider.get_income_statement(symbol, annual=False)
            
            if income_stmt is not None and len(income_stmt) >= 5:  # Need at least 5 quarters
                if 'eps' in income_stmt.columns:
                    current_eps = income_stmt['eps'].iloc[0]
                    year_ago_eps = income_stmt['eps'].iloc[4]
                    
                    # Only calculate growth if previous EPS was positive
                    if year_ago_eps > 0 and current_eps > 0:
                        eps_yoy_growth = ((current_eps / year_ago_eps) - 1) * 100
                        return {'rate': eps_yoy_growth, 'type': 'EPS YoY'}
        except Exception as e:
            logger.debug(f"Could not calculate quarterly growth for {symbol}: {e}")
        
        return None
    
    def screen_stocks(self, universe_df):
        """Override to store temporary data for formatting."""
        # Store temporary variables for reason formatting
        self._last_pe_ratio = None
        self._last_growth_rate = None
        self._last_growth_type = None
        
        # Call parent method
        result = super().screen_stocks(universe_df)
        
        # Clean up temporary variables
        if hasattr(self, '_last_pe_ratio'):
            delattr(self, '_last_pe_ratio')
        if hasattr(self, '_last_growth_rate'):
            delattr(self, '_last_growth_rate')
        if hasattr(self, '_last_growth_type'):
            delattr(self, '_last_growth_type')
        
        return result
    
    def get_data_for_symbol(self, symbol):
        """Override to store formatting data."""
        data = super().get_data_for_symbol(symbol)
        
        # Store data for formatting
        if data:
            self._last_pe_ratio = self.safe_float(data.get('PERatio'))
            growth_data = self._get_growth_rate_details(data)
            if growth_data:
                self._last_growth_rate = growth_data['rate']
                self._last_growth_type = growth_data['type']
        
        return data


def screen_for_peg_ratio(universe_df=None, max_peg_ratio=1.0, min_growth=5.0, force_refresh=False):
    """
    Legacy function for backward compatibility.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe
        max_peg_ratio (float): Maximum PEG ratio to include in results
        min_growth (float): Minimum expected growth rate percentage
        force_refresh (bool): Ignored - cache clearing is now global
        
    Returns:
        pd.DataFrame: DataFrame containing screening results
    """
    screener = PEGRatioScreener(max_peg_ratio=max_peg_ratio, min_growth=min_growth)
    
    # Use default universe if none provided
    if universe_df is None:
        from universe import get_stock_universe
        universe_df = get_stock_universe()
    
    return screener.screen_stocks(universe_df)
