"""
Stock screeners package for the stock screening pipeline.

This package contains 13 comprehensive screening strategies based on different financial metrics.
All screeners use the BaseScreener class-based approach and are accessed through
the registry system in utils.screener_registry.

Available Screeners:
    Multi-Factor:
        - CompositeScoreScreener: Multi-factor scoring across value, quality, growth, 
                                  momentum, analyst sentiment, and technical factors (RECOMMENDED)
    
    Value Investing:
        - PERatioScreener: Classic P/E ratio screening
        - PriceToBookScreener: Graham-style book value analysis  
        - PEGRatioScreener: Growth at reasonable price screening
        - HistoricValueScreener: Mean reversion value analysis
    
    Quality & Fundamental:
        - QualityScreener: Basic financial strength (10-point scale)
        - EnhancedQualityScreener: Advanced quality (0-100 granular scoring)
        - FCFYieldScreener: Free cash flow yield analysis
    
    Technical & Momentum:
        - MomentumScreener: 6M/3M performance analysis
        - SharpeRatioScreener: Risk-adjusted return screening
        - FiftyTwoWeekLowsScreener: Quality stocks near yearly lows
    
    Special Situations:
        - InsiderBuyingScreener: Pre-pump insider activity detection
        - AnalystSentimentMomentumScreener: Analyst sentiment momentum analysis

Usage:
    from utils import get_screener, list_screeners, run_screener
    
    # Get available screeners
    screeners = list_screeners()
    
    # Get a specific screener (RECOMMENDED: use composite_score)
    composite = get_screener("composite_score")
    results = composite.screen_stocks(universe_df)
    
    # Or run directly via main.py
    python main.py --universe sp500 --strategies composite_score --limit 30
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
from .historic_value import HistoricValueScreener
from .analyst_sentiment_momentum import AnalystSentimentMomentumScreener
from .composite_score import CompositeScoreScreener

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
    'FiftyTwoWeekLowsScreener',
    'HistoricValueScreener',
    'AnalystSentimentMomentumScreener',
    'CompositeScoreScreener'
]
