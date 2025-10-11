"""
Abstract base class for all stock screeners.

This module provides a common interface and shared functionality for all screening strategies,
including data fetching, error handling, and result formatting.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import pandas as pd
import numpy as np
from tqdm import tqdm
import data_providers


class BaseScreener(ABC):
    """
    Abstract base class for all stock screening strategies.
    
    Provides common functionality including:
    - Data provider integration
    - Progress tracking with tqdm
    - Error handling patterns
    - Threshold checking utilities
    """
    
    def __init__(self):
        """Initialize the screener with default data provider."""
        self.provider = data_providers.get_provider("financial_modeling_prep")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this screening strategy."""
        pass
    
    def get_strategy_description(self) -> str:
        """Return the description of this screening strategy."""
        return f'Analysis results for {self.get_strategy_name()} screening strategy.'
    
    @abstractmethod
    def calculate_score(self, data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate the screening score for a single stock.
        
        Args:
            data: Dictionary containing all relevant data for the stock
            
        Returns:
            Score for the stock, or None if stock should be excluded
        """
        pass
    
    @abstractmethod
    def meets_threshold(self, score: float) -> bool:
        """
        Check if a stock meets the minimum threshold for this strategy.
        
        Args:
            score: Calculated score for the stock
            
        Returns:
            True if the stock meets the threshold
        """
        pass
    
    def get_additional_data(self, symbol: str, data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Extract additional data fields specific to this screening strategy.
        Override this method to add strategy-specific data columns.
        
        Args:
            symbol: Stock symbol
            data: Company data from providers
            current_price: Current stock price
            
        Returns:
            Dictionary of additional data fields
        """
        return {}
    
    def format_reason(self, score: float, meets_threshold_flag: bool) -> str:
        """
        Format the screening reason for display.
        Override this method to provide custom reason formatting.
        
        Args:
            score: Calculated score for the stock
            meets_threshold_flag: Whether stock meets threshold
            
        Returns:
            Formatted reason string
        """
        return f"Score: {score:.2f}"
    
    def sort_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort the results DataFrame.
        Override this method to provide custom sorting.
        
        Args:
            df: Results DataFrame
            
        Returns:
            Sorted DataFrame
        """
        return df.sort_values('score')
    
    def get_data_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch all required data for a single symbol.
        Override this method to customize data fetching.
        
        Args:
            symbol: Stock symbol to fetch data for
            
        Returns:
            Dictionary containing all data needed for scoring, or None if data unavailable
        """
        try:
            # Default implementation - get company overview
            overview = self.provider.get_company_overview(symbol)
            if overview:
                overview['symbol'] = symbol  # Ensure symbol is in data
            return overview
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def screen_stocks(self, universe_df: pd.DataFrame) -> pd.DataFrame:
        """
        Screen all stocks in the universe using this strategy.
        
        Args:
            universe_df: DataFrame containing stock universe with 'symbol' column
            
        Returns:
            DataFrame with screening results, sorted by score
        """
        results = []
        strategy_name = self.get_strategy_name()
        
        self.logger.info(f"Running {strategy_name} screener on {len(universe_df)} stocks")
        
        # Get symbols list
        symbols = universe_df['symbol'].tolist()
        
        # Process each symbol
        for symbol in tqdm(symbols, desc=f"Screening for {strategy_name.lower()}", unit="symbol"):
            try:
                # Fetch data for this symbol
                data = self.get_data_for_symbol(symbol)
                if data is None:
                    continue
                
                # Calculate score
                score = self.calculate_score(data)
                if score is None:
                    continue
                
                # Check threshold
                meets_thresh = self.meets_threshold(score)
                
                # Get current price for additional data
                current_price = self._get_current_price(symbol, data)
                
                # Get additional data fields
                additional_data = self.get_additional_data(symbol, data, current_price)
                
                # Get basic company info
                company_name = data.get('Name', symbol)
                sector = data.get('Sector', 'Unknown')
                market_cap = data.get('MarketCapitalization', 0)
                
                # Format reason
                reason = self.format_reason(score, meets_thresh)
                
                # Build result record
                result = {
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'current_price': current_price,
                    'market_cap': market_cap,
                    'score': score,
                    'meets_threshold': meets_thresh,
                    'reason': reason,
                    **additional_data
                }
                
                results.append(result)
                
                if meets_thresh:
                    self.logger.info(f"Found {symbol}: {reason}")
                
            except Exception as e:
                self.logger.error(f"Error processing {symbol} for {strategy_name}: {e}")
                # Re-raise to stop execution on data provider failures
                raise Exception(f"Data provider failed for symbol {symbol}: {e}")
        
        # Convert to DataFrame
        if not results:
            self.logger.warning(f"No stocks found for {strategy_name} strategy")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        
        # Sort results using child class method
        df = self.sort_results(df)
        
        self.logger.info(f"{strategy_name} screener found {len(df)} stocks")
        return df
    
    def _get_current_price(self, symbol: str, data: Dict[str, Any]) -> float:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Stock symbol
            data: Company data dictionary
            
        Returns:
            Current stock price
        """
        # Try to get price from recent historical data
        try:
            price_data = self.provider.get_historical_prices(symbol, period="5d")
            if symbol in price_data and price_data[symbol] is not None and not price_data[symbol].empty:
                return price_data[symbol]['Close'].iloc[-1]
        except Exception:
            pass
        
        # Fall back to price from company data
        return self.safe_float(data.get('price', 0)) or 0
    
    @staticmethod
    def safe_float(value, default: float = 0.0) -> Optional[float]:
        """
        Safely convert a value to float, handling None and invalid values.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Float value or None if invalid
        """
        if value is None or value == '' or value == 'None':
            return None if default == 0.0 else default
        
        try:
            result = float(value)
            if np.isnan(result) or np.isinf(result):
                return None if default == 0.0 else default
            return result
        except (ValueError, TypeError):
            return None if default == 0.0 else default
    
    @staticmethod
    def safe_percentage(value, multiplier: float = 100.0, default: float = 0.0) -> Optional[float]:
        """
        Safely convert a decimal value to percentage.
        
        Args:
            value: Decimal value (e.g., 0.15)
            multiplier: Multiplier to convert to percentage (default: 100)
            default: Default value if conversion fails
            
        Returns:
            Percentage value (e.g., 15.0) or None if invalid
        """
        safe_val = BaseScreener.safe_float(value)
        if safe_val is None:
            return None if default == 0.0 else default
        return safe_val * multiplier