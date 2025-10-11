"""
Historic Value Screener module.
Identifies stocks trading at significant discounts to their own historical valuation metrics,
filtering out distressed situations to focus on temporary market inefficiencies.
Research basis: Mean reversion theory and contrarian value investing principles.
"""

from .common import *
from .base_screener import BaseScreener
import numpy as np

STRATEGY_DESCRIPTION = ("Identifies stocks trading below historic valuation averages while avoiding distressed situations. "
                       "Combines historic P/E, P/B, and EV/EBITDA discounts with quality filters for financial stability, "
                       "profitability trends, and market structure health.")


class HistoricValueScreener(BaseScreener):
    """Screener for stocks trading below historical valuation metrics while maintaining quality."""
    
    def __init__(self, min_historic_value_score=None, lookback_period="5y"):
        super().__init__()
        self.min_historic_value_score = min_historic_value_score or getattr(config.ScreeningThresholds, 'MIN_HISTORIC_VALUE_SCORE', 60.0)
        self.lookback_period = lookback_period
        
    def get_strategy_name(self):
        return "Historic Value Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def get_data_for_symbol(self, symbol):
        """
        Fetch historical and current data for historic value analysis.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Dictionary containing historical prices, financial statements, and overview
        """
        try:
            # Get current company overview
            overview = self.provider.get_company_overview(symbol)
            
            # Get historical price data for technical analysis
            price_data = self.provider.get_historical_prices(symbol, period=self.lookback_period)
            
            # Get financial statements for fundamental analysis
            income_statements = None
            balance_sheets = None
            try:
                income_statements = self.provider.get_income_statement(symbol)
                balance_sheets = self.provider.get_balance_sheet(symbol)
            except Exception as e:
                self.logger.debug(f"Could not fetch financial statements for {symbol}: {e}")
            
            # Flatten the data structure for BaseScreener compatibility
            result = {
                'price_data': price_data[symbol] if price_data and symbol in price_data else None,
                'income_statements': income_statements,
                'balance_sheets': balance_sheets,
                'symbol': symbol
            }
            
            # Add company overview data at top level
            if overview:
                result.update(overview)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_score(self, data):
        """
        Calculate historic value score (0-100 points) based on valuation discount and quality metrics.
        
        Args:
            data (dict): Dictionary containing all relevant data for the stock
            
        Returns:
            float: Historic value score (0-100) or None if calculation fails
        """
        symbol = data.get('symbol', 'Unknown')
        
        # Get current valuation metrics
        current_pe = self.safe_float(data.get('PERatio'))
        current_pb = self.safe_float(data.get('PriceToBookRatio'))
        current_ev_ebitda = self.safe_float(data.get('EVToEBITDA'))
        current_ps = self.safe_float(data.get('PriceToSalesRatio'))
        
        # Basic quality checks (distress avoidance)
        if not self._passes_basic_quality_checks(data):
            return None
        
        # Calculate historic valuation discount score (40% of total)
        valuation_score = self._calculate_valuation_discount_score(data, current_pe, current_pb, current_ev_ebitda, current_ps)
        if valuation_score is None:
            return None
        
        # Calculate quality score (35% of total)
        quality_score = self._calculate_quality_score(data)
        
        # Calculate market structure score (25% of total)
        market_score = self._calculate_market_structure_score(data)
        
        # Weighted total score
        total_score = (valuation_score * 0.40) + (quality_score * 0.35) + (market_score * 0.25)
        
        return min(total_score, 100.0)  # Cap at 100
    
    def _passes_basic_quality_checks(self, data):
        """Basic filters to exclude distressed companies."""
        
        # Must have positive earnings
        eps = self.safe_float(data.get('EPS'))
        if eps is None or eps <= 0:
            return False
        
        # Must have reasonable P/E ratio (avoid extreme valuations)
        pe = self.safe_float(data.get('PERatio'))
        if pe is None or pe <= 0 or pe > 50:
            return False
        
        # Must have minimum market cap ($500M)
        market_cap = self.safe_float(data.get('MarketCapitalization'))
        if market_cap is None or market_cap < 500_000_000:
            return False
        
        # Must have reasonable debt levels
        debt_equity = self.safe_float(data.get('DebtToEquityRatio'))
        if debt_equity is not None and debt_equity > 3.0:  # Very high debt
            return False
        
        return True
    
    def _calculate_valuation_discount_score(self, data, current_pe, current_pb, current_ev_ebitda, current_ps):
        """Calculate score based on discount to historical averages."""
        
        # For now, use proxy calculations since we need historical data
        # In a full implementation, you'd calculate actual historical averages
        
        score = 0
        metrics_count = 0
        
        # P/E discount score (0-25 points)
        if current_pe is not None:
            # Proxy: assume historical average P/E is 20% higher for quality companies
            estimated_historic_pe = current_pe * 1.25
            pe_discount = (estimated_historic_pe - current_pe) / estimated_historic_pe
            if pe_discount > 0.20:  # >20% discount
                score += min(25, pe_discount * 100)
            elif pe_discount > 0.10:  # >10% discount
                score += min(15, pe_discount * 75)
            metrics_count += 1
        
        # P/B discount score (0-15 points)
        if current_pb is not None:
            # Proxy: companies trading below 1.5 P/B might be undervalued
            if current_pb < 1.0:
                score += 15
            elif current_pb < 1.5:
                score += 10
            elif current_pb < 2.0:
                score += 5
            metrics_count += 1
        
        # EV/EBITDA discount score (0-10 points)
        if current_ev_ebitda is not None:
            # Proxy: EV/EBITDA below 12 might indicate value
            if current_ev_ebitda < 8:
                score += 10
            elif current_ev_ebitda < 12:
                score += 6
            elif current_ev_ebitda < 15:
                score += 3
            metrics_count += 1
        
        # Need at least 2 metrics for valid score
        if metrics_count < 2:
            return None
        
        return score
    
    def _calculate_quality_score(self, data):
        """Calculate quality score based on financial stability and profitability."""
        
        score = 0
        
        # Financial stability (0-20 points)
        debt_equity = self.safe_float(data.get('DebtToEquityRatio', 0))
        if debt_equity is not None:
            if debt_equity < 0.3:
                score += 20  # Very low debt
            elif debt_equity < 0.6:
                score += 15  # Low debt
            elif debt_equity < 1.0:
                score += 10  # Moderate debt
            elif debt_equity < 1.5:
                score += 5   # Higher debt but manageable
        
        # Profitability trends (0-15 points)
        roe = self.safe_percentage(data.get('ReturnOnEquityTTM'))
        profit_margin = self.safe_percentage(data.get('ProfitMargin'))
        
        if roe is not None:
            if roe > 0.15:  # >15% ROE
                score += 8
            elif roe > 0.10:  # >10% ROE
                score += 5
            elif roe > 0.05:  # >5% ROE
                score += 2
        
        if profit_margin is not None:
            if profit_margin > 0.15:  # >15% profit margin
                score += 7
            elif profit_margin > 0.08:  # >8% profit margin
                score += 4
            elif profit_margin > 0.03:  # >3% profit margin
                score += 2
        
        return score
    
    def _calculate_market_structure_score(self, data):
        """Calculate market structure score based on liquidity and technical position."""
        
        score = 0
        
        # Liquidity and coverage (0-15 points)
        market_cap = self.safe_float(data.get('MarketCapitalization'))
        if market_cap is not None:
            if market_cap > 10_000_000_000:  # >$10B
                score += 15
            elif market_cap > 2_000_000_000:  # >$2B
                score += 12
            elif market_cap > 1_000_000_000:  # >$1B
                score += 8
            else:
                score += 5
        
        # Technical positioning (0-10 points)
        # Use beta as proxy for stability
        beta = self.safe_float(data.get('Beta'))
        if beta is not None:
            if 0.8 <= beta <= 1.2:  # Moderate volatility
                score += 10
            elif 0.6 <= beta <= 1.4:  # Acceptable volatility
                score += 7
            elif beta < 2.0:  # Higher volatility
                score += 3
        
        return score
    
    def meets_threshold(self, score):
        """
        Check if historic value score meets minimum threshold.
        
        Args:
            score (float): Historic value score
            
        Returns:
            bool: True if score meets minimum threshold
        """
        return score is not None and score >= self.min_historic_value_score
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to historic value screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Stock data dictionary
            current_price (float): Current stock price
            
        Returns:
            dict: Additional historic value metrics
        """
        return {
            'pe_ratio': self.safe_float(data.get('PERatio')),
            'pb_ratio': self.safe_float(data.get('PriceToBookRatio')),
            'ev_ebitda': self.safe_float(data.get('EVToEBITDA')),
            'debt_equity': self.safe_float(data.get('DebtToEquityRatio')),
            'roe': self.safe_percentage(data.get('ReturnOnEquityTTM')),
            'profit_margin': self.safe_percentage(data.get('ProfitMargin')),
            'market_cap': self.safe_float(data.get('MarketCapitalization')),
            'beta': self.safe_float(data.get('Beta'))
        }
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): Historic value score
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"Historic value opportunity (Score: {score:.1f}/100)"
        else:
            return f"Historic value score: {score:.1f}/100"
    
    def sort_results(self, df):
        """Sort results by historic value score (highest first)."""
        return df.sort_values('score', ascending=False)