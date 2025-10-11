"""
Sharpe Ratio Screener module.
Screens for stocks with high risk-adjusted returns (Sharpe ratio).
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Identifies stocks with superior risk-adjusted returns. Higher Sharpe ratios indicate better return per unit of risk taken, with values above 1.0 considered good."


class SharpeRatioScreener(BaseScreener):
    """Screener for stocks with high Sharpe ratios (risk-adjusted returns)."""
    
    def __init__(self, min_sharpe_ratio=None, lookback_period="1y"):
        super().__init__()
        self.min_sharpe_ratio = min_sharpe_ratio or getattr(config.ScreeningThresholds, 'MIN_SHARPE_RATIO', 1.0)
        self.lookback_period = lookback_period
        self.risk_free_rate = 0.04  # 4% annual risk-free rate assumption
    
    def get_strategy_name(self):
        return "Sharpe Ratio Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def get_data_for_symbol(self, symbol):
        """
        Fetch historical price data needed for Sharpe ratio calculation.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Dictionary containing historical data and overview
        """
        try:
            # Get historical price data for Sharpe ratio calculation
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
        Calculate Sharpe ratio for the stock.
        
        Args:
            data (dict): Dictionary containing price data and overview
            
        Returns:
            float: Sharpe ratio or None if calculation fails
        """
        price_data = data.get('price_data')
        
        if price_data is None or len(price_data) < 30:
            return None
        
        try:
            # Calculate daily returns
            prices = price_data['Close'].values
            daily_returns = np.diff(prices) / prices[:-1]
            
            if len(daily_returns) < 30:  # Need sufficient data points
                return None
            
            # Calculate annualized return and volatility
            mean_return = np.mean(daily_returns)
            volatility = np.std(daily_returns, ddof=1)
            
            # Annualize (assuming ~252 trading days per year)
            annualized_return = mean_return * 252
            annualized_volatility = volatility * np.sqrt(252)
            
            if annualized_volatility == 0:
                return None
            
            # Calculate Sharpe ratio
            excess_return = annualized_return - self.risk_free_rate
            sharpe_ratio = excess_return / annualized_volatility
            
            return sharpe_ratio
            
        except Exception as e:
            symbol = data.get('symbol', 'unknown')
            self.logger.error(f"Error calculating Sharpe ratio for {symbol}: {e}")
            return None
    
    def meets_threshold(self, score):
        """
        Check if Sharpe ratio meets minimum threshold.
        
        Args:
            score (float): Sharpe ratio
            
        Returns:
            bool: True if Sharpe ratio exceeds minimum threshold
        """
        return score is not None and score >= self.min_sharpe_ratio
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to Sharpe ratio screening.
        
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
        
        if price_data is not None and len(price_data) >= 30:
            try:
                prices = price_data['Close'].values
                daily_returns = np.diff(prices) / prices[:-1]
                
                # Calculate individual components
                mean_return = np.mean(daily_returns)
                volatility = np.std(daily_returns, ddof=1)
                
                annualized_return = mean_return * 252
                annualized_volatility = volatility * np.sqrt(252)
                
                additional.update({
                    'annualized_return': annualized_return,
                    'annualized_volatility': annualized_volatility,
                    'risk_free_rate': self.risk_free_rate
                })
                
                # Calculate max drawdown
                cumulative_returns = np.cumprod(1 + daily_returns)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdowns = (cumulative_returns - running_max) / running_max
                max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else None
                additional['max_drawdown'] = max_drawdown
                
            except Exception as e:
                self.logger.debug(f"Error calculating additional metrics for {symbol}: {e}")
        
        return additional
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): Sharpe ratio
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"Strong risk-adjusted returns (Sharpe = {score:.2f})"
        else:
            return f"Sharpe ratio: {score:.2f}"
    
    def sort_results(self, df):
        """Sort results by Sharpe ratio (highest first)."""
        return df.sort_values('score', ascending=False)
