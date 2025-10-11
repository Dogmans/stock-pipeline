"""
Momentum Screener module.
Screens for stocks with strong price momentum based on 6-month and 3-month returns.
Research basis: Jegadeesh & Titman (1993) - Returns to Buying Winners and Selling Losers.
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Identifies stocks with strong recent performance trends using 6-month and 3-month weighted returns. Higher momentum scores indicate stronger recent price performance."


class MomentumScreener(BaseScreener):
    """Screener for stocks with strong price momentum."""
    
    def __init__(self, min_momentum_score=None, lookback_period="7mo"):
        super().__init__()
        self.min_momentum_score = min_momentum_score or getattr(config.ScreeningThresholds, 'MIN_MOMENTUM_SCORE', 15.0)
        self.lookback_period = lookback_period
    
    def get_strategy_name(self):
        return "Momentum Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def get_data_for_symbol(self, symbol):
        """
        Fetch historical price data for momentum calculation.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Dictionary containing historical data and overview
        """
        try:
            # Get historical price data for momentum calculation (7 months to skip most recent month)
            price_data = self.provider.get_historical_prices(symbol, period=self.lookback_period)
            overview = self.provider.get_company_overview(symbol)
            
            if price_data is None or symbol not in price_data or price_data[symbol].empty:
                return None
                
            # Flatten the data structure so BaseScreener can access company fields directly
            result = {
                'price_data': price_data[symbol],
                'symbol': symbol
            }
            
            # Add company overview data at top level for BaseScreener compatibility
            if overview:
                result.update(overview)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_score(self, data):
        """
        Calculate momentum score based on 6-month and 3-month weighted returns.
        
        Args:
            data (dict): Dictionary containing price data and overview
            
        Returns:
            float: Momentum score (percentage) or None if calculation fails
        """
        price_data = data.get('price_data')
        
        if price_data is None or len(price_data) < 90:  # Need at least ~3 months of data
            return None
        
        try:
            # Sort by date and get closing prices
            df = price_data.sort_index()
            prices = df['Close'].values
            
            if len(prices) < 90:
                return None
            
            current_price = prices[-1]
            
            # Skip most recent month (last ~21 trading days) to avoid reversal effects
            skip_recent_days = min(21, len(prices) // 7)  # Skip ~1 month or 1/7th of data
            reference_price = prices[-(skip_recent_days + 1)] if len(prices) > skip_recent_days else prices[-1]
            
            # Calculate 6-month return (from 6 months ago to 1 month ago)
            six_month_idx = min(126 + skip_recent_days, len(prices) - 1)  # ~6 months + skip period
            if six_month_idx < len(prices):
                six_month_price = prices[-(six_month_idx + 1)]
                six_month_return = ((reference_price - six_month_price) / six_month_price) * 100
            else:
                six_month_return = None
            
            # Calculate 3-month return (from 3 months ago to 1 month ago)
            three_month_idx = min(63 + skip_recent_days, len(prices) - 1)  # ~3 months + skip period
            if three_month_idx < len(prices):
                three_month_price = prices[-(three_month_idx + 1)]
                three_month_return = ((reference_price - three_month_price) / three_month_price) * 100
            else:
                three_month_return = None
            
            # Need at least one timeframe to calculate momentum
            if six_month_return is None and three_month_return is None:
                return None
            
            # Weighted momentum score: 6-month (60%) + 3-month (40%)
            if six_month_return is not None and three_month_return is not None:
                momentum_score = (six_month_return * 0.6) + (three_month_return * 0.4)
            elif six_month_return is not None:
                momentum_score = six_month_return
            else:
                momentum_score = three_month_return
            
            return momentum_score
            
        except Exception as e:
            symbol = data.get('symbol', 'unknown')
            self.logger.error(f"Error calculating momentum for {symbol}: {e}")
            return None
    
    def meets_threshold(self, score):
        """
        Check if momentum meets minimum threshold.
        
        Args:
            score (float): Momentum score (percentage)
            
        Returns:
            bool: True if momentum exceeds minimum threshold
        """
        return score is not None and score >= self.min_momentum_score
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to momentum screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Stock data dictionary
            current_price (float): Current stock price
            
        Returns:
            dict: Additional data fields
        """
        additional = {}
        price_data = data.get('price_data')
        overview = data.get('overview', {})
        
        if price_data is not None and len(price_data) >= 63:
            try:
                df = price_data.sort_index()
                prices = df['Close'].values
                
                # Calculate individual period returns for additional context
                skip_recent_days = min(21, len(prices) // 7)
                reference_price = prices[-(skip_recent_days + 1)] if len(prices) > skip_recent_days else prices[-1]
                
                # Individual returns
                if len(prices) >= 126 + skip_recent_days:
                    six_month_price = prices[-(126 + skip_recent_days + 1)]
                    additional['six_month_return'] = ((reference_price - six_month_price) / six_month_price) * 100
                
                if len(prices) >= 63 + skip_recent_days:
                    three_month_price = prices[-(63 + skip_recent_days + 1)]
                    additional['three_month_return'] = ((reference_price - three_month_price) / three_month_price) * 100
                
                # Recent performance (last month for comparison)
                additional['one_month_return'] = ((prices[-1] - reference_price) / reference_price) * 100
                
                # Calculate volatility
                if len(prices) >= 30:
                    returns = np.diff(prices) / prices[:-1]
                    additional['volatility_30d'] = np.std(returns[-30:]) * np.sqrt(252) * 100  # Annualized volatility %
                
            except Exception as e:
                self.logger.debug(f"Error calculating additional metrics for {symbol}: {e}")
        
        return additional
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): Momentum score (percentage)
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"Strong momentum ({score:.1f}% weighted return)"
        else:
            return f"Momentum score: {score:.1f}%"
    
    def sort_results(self, df):
        """Sort results by momentum score (highest first)."""
        return df.sort_values('score', ascending=False)
