"""
Free Cash Flow Yield Screener module.
Screens for stocks with high free cash flow yield relative to market capitalization.
Research basis: Joel Greenblatt's "Magic Formula" and FCF yield as predictor of long-term returns.
"""

from .common import *
from .base_screener import BaseScreener

STRATEGY_DESCRIPTION = "Screens for stocks with high free cash flow relative to market capitalization. Higher FCF yields may indicate better value and cash-generating ability."


class FCFYieldScreener(BaseScreener):
    """Screener for stocks with high free cash flow yield."""
    
    def __init__(self, min_fcf_yield=None):
        super().__init__()
        self.min_fcf_yield = min_fcf_yield or getattr(config.ScreeningThresholds, 'MIN_FCF_YIELD', 8.0)
    
    def get_strategy_name(self):
        return "FCF Yield Screener"
    
    def get_strategy_description(self):
        return STRATEGY_DESCRIPTION
    
    def get_data_for_symbol(self, symbol):
        """
        Fetch data needed for FCF yield calculation.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Dictionary containing overview and cash flow data
        """
        try:
            # Get company overview and cash flow data
            overview = self.provider.get_company_overview(symbol)
            
            # Try to get cash flow data
            cash_flow = None
            try:
                cash_flow = self.provider.get_cash_flow(symbol)
            except Exception as e:
                self.logger.debug(f"Could not fetch cash flow for {symbol}: {e}")
            
            # Flatten the data structure for BaseScreener compatibility
            result = {
                'cash_flow': cash_flow,
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
        Calculate free cash flow yield.
        
        Args:
            data (dict): Company data from providers
            
        Returns:
            float: FCF yield percentage or None if calculation fails
        """
        cash_flow = data.get('cash_flow')
        
        # Get market cap from the flattened data structure
        market_cap = self.safe_float(data.get('MarketCapitalization'))
        if not market_cap or market_cap <= 0:
            return None
        
        # Try to calculate FCF from cash flow statement
        free_cash_flow = None
        
        if cash_flow is not None and hasattr(cash_flow, 'iloc') and len(cash_flow) > 0:
            try:
                # Get most recent year's data (first row is usually most recent)
                latest_cf = cash_flow.iloc[0] if len(cash_flow) > 0 else None
                if latest_cf is not None:
                    # Try different field names for operating cash flow and capex
                    operating_cf = self.safe_float(
                        latest_cf.get('operatingCashFlow') or 
                        latest_cf.get('netCashProvidedByOperatingActivities') or
                        latest_cf.get('Operating Cash Flow')
                    )
                    capex = self.safe_float(
                        latest_cf.get('capitalExpenditure') or 
                        latest_cf.get('capitalExpenditures') or
                        latest_cf.get('Capital Expenditures')
                    )
                    
                    if operating_cf is not None and capex is not None:
                        # FCF = Operating Cash Flow - Capital Expenditures
                        # Note: capex is usually negative, so we add it (subtract absolute value)
                        free_cash_flow = operating_cf + capex  # capex is negative
                        
            except Exception as e:
                self.logger.debug(f"Error calculating FCF from cash flow statement for {data.get('symbol', 'unknown')}: {e}")
        
        # If we couldn't calculate FCF, return None (no score)
        if free_cash_flow is None or free_cash_flow <= 0:
            return None
        
        # Calculate FCF yield as percentage
        fcf_yield = (free_cash_flow / market_cap) * 100
        
        return fcf_yield
    
    def meets_threshold(self, score):
        """
        Check if FCF yield meets minimum threshold.
        
        Args:
            score (float): FCF yield percentage
            
        Returns:
            bool: True if FCF yield exceeds minimum threshold
        """
        return score is not None and score >= self.min_fcf_yield
    
    def get_additional_data(self, symbol, data, current_price):
        """
        Extract additional data fields specific to FCF yield screening.
        
        Args:
            symbol (str): Stock symbol
            data (dict): Stock data dictionary
            current_price (float): Current stock price
            
        Returns:
            dict: Additional FCF-related metrics
        """
        overview = data.get('overview', {})
        cash_flow = data.get('cash_flow')
        
        additional = {}
        
        # Add FCF components if available
        fcf_ttm = self.safe_float(overview.get('FreeCashFlowTTM'))
        if fcf_ttm:
            additional['free_cash_flow_ttm'] = fcf_ttm
        
        # Add operating cash flow if available
        if cash_flow is not None and not cash_flow.empty and len(cash_flow) > 0:
            try:
                latest_cf = cash_flow.iloc[0]
                operating_cf = self.safe_float(latest_cf.get('operatingCashFlow', latest_cf.get('netCashProvidedByOperatingActivities')))
                capex = self.safe_float(latest_cf.get('capitalExpenditure', latest_cf.get('capitalExpenditures')))
                
                if operating_cf:
                    additional['operating_cash_flow'] = operating_cf
                if capex:
                    additional['capital_expenditure'] = capex
                
            except Exception as e:
                self.logger.debug(f"Error extracting cash flow details for {symbol}: {e}")
        
        return additional
    
    def format_reason(self, score, meets_threshold_flag):
        """
        Format the screening reason for display.
        
        Args:
            score (float): FCF yield percentage
            meets_threshold_flag (bool): Whether stock meets threshold
            
        Returns:
            str: Formatted reason string
        """
        if meets_threshold_flag:
            return f"High FCF yield ({score:.1f}%)"
        else:
            return f"FCF yield: {score:.1f}%"
    
    def sort_results(self, df):
        """Sort results by FCF yield (highest first)."""
        return df.sort_values('score', ascending=False)
