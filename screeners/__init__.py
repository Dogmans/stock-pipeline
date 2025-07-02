"""
Stock screeners package for the stock screening pipeline.
This package contains various screening strategies based on different financial metrics.
"""

# Import all individual screener modules
from . import pe_ratio
from . import price_to_book
from . import fifty_two_week_lows
from . import fallen_ipos
from . import turnaround_candidates
from . import peg_ratio
from . import combined
from . import sector_corrections

# Import utility functions
from .utils import get_available_screeners, run_all_screeners

# Define the main screener functions to expose at the package level
# This makes them accessible via screeners.function_name
screen_for_pe_ratio = pe_ratio.screen_for_pe_ratio
screen_for_price_to_book = price_to_book.screen_for_price_to_book
screen_for_52_week_lows = fifty_two_week_lows.screen_for_52_week_lows
screen_for_fallen_ipos = fallen_ipos.screen_for_fallen_ipos
screen_for_turnaround_candidates = turnaround_candidates.screen_for_turnaround_candidates
screen_for_peg_ratio = peg_ratio.screen_for_peg_ratio
screen_for_combined = combined.screen_for_combined
screen_for_sector_corrections = sector_corrections.screen_for_sector_corrections

# Add aliases for backward compatibility with older tests
pe_ratio_screener = pe_ratio.screen_for_pe_ratio
price_to_book_screener = price_to_book.screen_for_price_to_book
fifty_two_week_low_screener = fifty_two_week_lows.screen_for_52_week_lows

# Add exported symbols to __all__ for better import control
__all__ = [
    'screen_for_pe_ratio', 'screen_for_price_to_book', 'screen_for_52_week_lows',
    'screen_for_fallen_ipos', 'screen_for_turnaround_candidates', 'screen_for_peg_ratio',
    'screen_for_combined', 'screen_for_sector_corrections', 'pe_ratio_screener', 
    'price_to_book_screener', 'fifty_two_week_low_screener', 'get_available_screeners', 
    'run_all_screeners'
]
