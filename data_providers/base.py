"""
Base data provider utilities for stock data retrieval.

This module defines a base class with common utilities that data providers can optionally extend.
Each provider can now use their own method names that match their specific APIs.
"""
import pandas as pd
from typing import Dict, List, Union, Optional, Any

class BaseDataProvider:
    """
    Base class for stock data providers with common utilities.
    
    This class provides common utility methods for data providers
    but no longer enforces a specific interface. Providers are free
    to use method names that match their specific APIs.
    """
    
    def get_fundamental_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Example utility method for retrieving fundamental data.
        
        NOTE: This is now just a template/example. Providers should implement
        their own version according to their specific APIs, and they are free
        to use different method names that match their API's naming conventions.
        
        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            
        Returns:
            Dictionary of fundamental data
        """
        raise NotImplementedError("This method should be implemented by provider subclasses using their API-specific methods")
    
    def parallel_data_fetcher(self, symbols: List[str],
                               fetch_method_name: str,
                               force_refresh: bool = False,
                               max_workers: int = 5,
                               rate_limit: Optional[int] = None,
                               **method_kwargs) -> Dict[str, Any]:
        """
        Utility method for parallel data fetching.
        
        This generic method uses a ThreadPoolExecutor to fetch data for multiple symbols
        in parallel using any method available in the provider.
        
        Args:
            symbols: List of stock symbols
            fetch_method_name: Name of the method to call for each symbol
            force_refresh: Whether to bypass cache and fetch fresh data
            max_workers: Maximum number of parallel workers
            rate_limit: Maximum requests per minute (None for no limit)
            **method_kwargs: Additional keyword arguments to pass to the method
            
        Returns:
            Dictionary mapping each symbol to its fetched data
        """
        import concurrent.futures
        import time
        from utils.logger import get_logger
        
        logger = get_logger(__name__)
        results = {}
        
        if not hasattr(self, fetch_method_name):
            logger.error(f"Method {fetch_method_name} not found in provider {self.get_provider_name()}")
            return results
            
        fetch_method = getattr(self, fetch_method_name)
        
        def fetch_for_symbol(index, symbol):
            if rate_limit and index > 0 and index % rate_limit == 0:
                time.sleep(60)  # Sleep for 60 seconds to respect rate limit
                
            try:
                return symbol, fetch_method(symbol, force_refresh=force_refresh, **method_kwargs)
            except Exception as e:
                logger.error(f"Error fetching data for {symbol} using {fetch_method_name}: {e}")
                return symbol, None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_for_symbol, i, symbol) 
                      for i, symbol in enumerate(symbols)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    symbol, data = future.result()
                    if data is not None:
                        results[symbol] = data
                except Exception as e:
                    logger.error(f"Error processing future: {e}")
        
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
