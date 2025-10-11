"""
Stock screeners package for the stock screening pipeline.

This package contains various screening strategies based on different financial metrics.
All screeners now use the BaseScreener class-based approach and are accessed through
the registry system in utils.screener_registry.

Usage:
    from utils import get_screener, list_screeners, run_screener
    
    # Get available screeners
    screeners = list_screeners()
    
    # Get a specific screener
    pe_screener = get_screener("pe_ratio", max_pe=20.0)
    results = pe_screener.screen_stocks(universe_df)
    
    # Or run directly
    results = run_screener("pe_ratio", universe_df, max_pe=20.0)
"""

# Import screener classes for direct access if needed
from .pe_ratio import PERatioScreener
from .peg_ratio import PEGRatioScreener
from .price_to_book import PriceToBookScreener
from .sharpe_ratio import SharpeRatioScreener
from .momentum import MomentumScreener
from .quality import QualityScreener
from .free_cash_flow_yield import FCFYieldScreener
from .enhanced_quality import EnhancedQualityScreener
from .insider_buying import InsiderBuyingScreener
from .fifty_two_week_lows import FiftyTwoWeekLowsScreener

# Combined screener can be imported separately to avoid circular imports
# from .combined import run_screeners_with_registry

__all__ = [
    'PERatioScreener',
    'PEGRatioScreener', 
    'PriceToBookScreener',
    'SharpeRatioScreener',
    'MomentumScreener',
    'QualityScreener',
    'FCFYieldScreener',
    'EnhancedQualityScreener',
    'InsiderBuyingScreener',
    'FiftyTwoWeekLowsScreener'
]
