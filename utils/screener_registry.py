"""
Screener registry for the stock pipeline.
"""

import logging
from typing import Dict, Type, Optional, Any
from screeners.base_screener import BaseScreener

logger = logging.getLogger(__name__)

# Global screener registry
_screener_registry: Dict[str, Type[BaseScreener]] = {}


def register_screener(name: str, screener_class: Type[BaseScreener]):
    """
    Register a screener class in the global registry.
    
    Args:
        name (str): Name to register the screener under
        screener_class (Type[BaseScreener]): Screener class to register
    """
    if not issubclass(screener_class, BaseScreener):
        raise ValueError(f"Screener class {screener_class.__name__} must inherit from BaseScreener")
    
    _screener_registry[name] = screener_class
    logger.debug(f"Registered screener: {name} -> {screener_class.__name__}")


def get_screener(name: str, **kwargs) -> Optional[BaseScreener]:
    """
    Get a screener instance by name.
    
    Args:
        name (str): Name of the screener to retrieve
        **kwargs: Arguments to pass to screener constructor
        
    Returns:
        BaseScreener: Instance of the requested screener, or None if not found
    """
    screener_class = _screener_registry.get(name)
    if screener_class is None:
        logger.error(f"Screener '{name}' not found in registry")
        return None
    
    try:
        return screener_class(**kwargs)
    except Exception as e:
        logger.error(f"Failed to create screener '{name}': {e}")
        return None


def list_screeners() -> Dict[str, str]:
    """
    List all registered screeners.
    
    Returns:
        Dict[str, str]: Dictionary mapping screener names to their descriptions
    """
    screeners = {}
    for name, screener_class in _screener_registry.items():
        try:
            # Create a temporary instance to get the description
            temp_instance = screener_class()
            screeners[name] = temp_instance.get_strategy_description()
        except Exception as e:
            screeners[name] = f"Error getting description: {e}"
    
    return screeners


def auto_register_screeners():
    """
    Automatically register all available screener classes.
    This function imports screener modules and registers their classes.
    """
    try:
        # Import screener classes
        from screeners.pe_ratio import PERatioScreener
        from screeners.peg_ratio import PEGRatioScreener
        from screeners.price_to_book import PriceToBookScreener
        from screeners.sharpe_ratio import SharpeRatioScreener
        from screeners.momentum import MomentumScreener
        from screeners.quality import QualityScreener
        from screeners.free_cash_flow_yield import FCFYieldScreener
        from screeners.enhanced_quality import EnhancedQualityScreener
        from screeners.insider_buying import InsiderBuyingScreener
        from screeners.fifty_two_week_lows import FiftyTwoWeekLowsScreener
        from screeners.historic_value import HistoricValueScreener
        from screeners.analyst_sentiment_momentum import AnalystSentimentMomentumScreener
        
        # Register the screeners
        register_screener("pe_ratio", PERatioScreener)
        register_screener("peg_ratio", PEGRatioScreener)
        register_screener("price_to_book", PriceToBookScreener)
        register_screener("sharpe_ratio", SharpeRatioScreener)
        register_screener("momentum", MomentumScreener)
        register_screener("quality", QualityScreener)
        register_screener("fcf_yield", FCFYieldScreener)
        register_screener("enhanced_quality", EnhancedQualityScreener)
        register_screener("insider_buying", InsiderBuyingScreener)
        register_screener("fifty_two_week_lows", FiftyTwoWeekLowsScreener)
        register_screener("historic_value", HistoricValueScreener)
        register_screener("analyst_sentiment_momentum", AnalystSentimentMomentumScreener)
        register_screener("historic_value", HistoricValueScreener)
        
        logger.info(f"Auto-registered {len(_screener_registry)} screeners")
        
    except ImportError as e:
        logger.error(f"Failed to import screener classes: {e}")
    except Exception as e:
        logger.error(f"Failed to auto-register screeners: {e}")


def run_screener(name: str, universe_df, **kwargs):
    """
    Run a screener by name on the given universe.
    
    Args:
        name (str): Name of the screener to run
        universe_df (DataFrame): Stock universe to screen
        **kwargs: Additional arguments to pass to screener constructor
        
    Returns:
        DataFrame: Screening results, or empty DataFrame if screener not found
    """
    screener = get_screener(name, **kwargs)
    if screener is None:
        logger.error(f"Cannot run screener '{name}' - not found in registry")
        import pandas as pd
        return pd.DataFrame()
    
    return screener.screen_stocks(universe_df)


# Auto-register screeners when this module is imported
auto_register_screeners()