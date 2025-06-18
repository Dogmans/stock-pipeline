"""
Base data provider interface for stock data retrieval.

This module defines the abstract base class that all data providers must implement.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Union, Optional, Any

class BaseDataProvider(ABC):
    """
    Abstract base class for stock data providers.
    
    All concrete data provider classes should extend this base class
    and implement its abstract methods to ensure a consistent interface.
    """
    
    @abstractmethod
    def get_historical_prices(self, symbols: Union[str, List[str]], 
                             period: str = "1y", 
                             interval: str = "1d",
                             force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get historical price data for the specified symbols.
        
        Args:
            symbols: Single symbol or list of stock symbols
            period: Time period to retrieve (e.g., '1y', '6m', '1d')
            interval: Data interval (e.g., '1d', '1h', '5m')
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary mapping each symbol to its historical price DataFrame
            Each DataFrame has columns: Open, High, Low, Close, Volume
        """
        pass
    
    @abstractmethod
    def get_income_statement(self, symbol: str, 
                            annual: bool = True,
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        Get income statement data for the specified symbol.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing income statement data
        """
        pass
    
    @abstractmethod
    def get_balance_sheet(self, symbol: str, 
                         annual: bool = True,
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Get balance sheet data for the specified symbol.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing balance sheet data
        """
        pass
    
    @abstractmethod
    def get_cash_flow(self, symbol: str, 
                     annual: bool = True,
                     force_refresh: bool = False) -> pd.DataFrame:
        """
        Get cash flow data for the specified symbol.
        
        Args:
            symbol: Stock symbol
            annual: If True, get annual data, otherwise quarterly
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            DataFrame containing cash flow data
        """
        pass
    
    @abstractmethod
    def get_company_overview(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get company overview data for the specified symbol.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing company overview data
        """
        pass
    
    def get_fundamental_data(self, symbol: str, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive fundamental data for the specified symbol.
        
        This method provides a unified interface to retrieve all fundamental
        data in a single call. The default implementation calls the individual
        methods, but providers can override this for more efficient retrieval.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary with keys: 'income_statement', 'balance_sheet', 
                                  'cash_flow', and 'overview'
        """
        return {
            'income_statement': self.get_income_statement(symbol, force_refresh=force_refresh),
            'balance_sheet': self.get_balance_sheet(symbol, force_refresh=force_refresh),
            'cash_flow': self.get_cash_flow(symbol, force_refresh=force_refresh),
            'overview': self.get_company_overview(symbol, force_refresh=force_refresh)
        }
    
    def get_batch_fundamental_data(self, symbols: List[str], 
                                  force_refresh: bool = False,
                                  max_workers: int = 5,
                                  rate_limit: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive fundamental data for multiple symbols in batch.
        
        This method provides a batched interface for retrieving fundamental data.
        The default implementation uses a ThreadPoolExecutor to parallelize requests,
        but providers can override this for more efficient batch operations.
        
        Args:
            symbols: List of stock symbols
            force_refresh: Whether to bypass cache and fetch fresh data
            max_workers: Maximum number of parallel workers
            rate_limit: Maximum requests per minute (None for no limit)
            
        Returns:
            Dictionary mapping each symbol to its fundamental data
        """
        import concurrent.futures
        import time
        
        results = {}
        
        def get_data_for_symbol(index, symbol):
            if rate_limit and index > 0 and index % rate_limit == 0:
                time.sleep(60)  # Sleep for 60 seconds to respect rate limit
                
            try:
                return symbol, self.get_fundamental_data(symbol, force_refresh=force_refresh)
            except Exception as e:
                import logging
                logging = logging.getLogger(__name__)
                logging.error(f"Error getting data for {symbol}: {e}")
                return symbol, None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(get_data_for_symbol, i, symbol) 
                      for i, symbol in enumerate(symbols)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    symbol, data = future.result()
                    if data is not None:
                        results[symbol] = data
                except Exception as e:
                    import logging
                    logging = logging.getLogger(__name__)
                    logging.error(f"Error processing future: {e}")
        
        return results
    
    def get_provider_name(self) -> str:
        """
        Get the name of this data provider.
        
        Returns:
            String name of the provider
        """
        return self.__class__.__name__
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this data provider.
        
        Returns:
            Dictionary with provider information
        """
        return {
            'name': self.get_provider_name(),
            'rate_limit': getattr(self, 'RATE_LIMIT', None),
            'daily_limit': getattr(self, 'DAILY_LIMIT', None),
        }
