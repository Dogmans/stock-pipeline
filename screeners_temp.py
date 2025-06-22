"""
Stock screeners module for the stock screening pipeline.
Implements the screening strategies based on the "15 Tools for Stock Picking" series.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
import datetime
import yfinance as yf

import config
from universe import get_stock_universe
from stock_data import get_historical_prices, fetch_52_week_lows
from market_data import is_market_in_correction, get_sector_performances
from data_processing import (
    calculate_technical_indicators, 
    calculate_price_statistics,
    analyze_debt_and_cash
)
from utils.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Ensure results directory exists
Path(config.RESULTS_DIR).mkdir(parents=True, exist_ok=True)

# Add aliases for screener functions to match what tests are expecting
def price_to_book_screener(*args, **kwargs):
    """Alias for screen_for_price_to_book to maintain test compatibility"""
    return screen_for_price_to_book(*args, **kwargs)

def pe_ratio_screener(*args, **kwargs):
    """Alias for screen_for_pe_ratio to maintain test compatibility"""
    return screen_for_pe_ratio(*args, **kwargs)

def fifty_two_week_low_screener(*args, **kwargs):
    """Alias for screen_for_52_week_lows to maintain test compatibility"""
    return screen_for_52_week_lows(*args, **kwargs)

def get_available_screeners():
    """
    Get a list of all available screener strategy names.
    
    Returns:
        list: List of strategy names (strings)
    """
    # List all the screening functions in this module
    screener_functions = [
        name.replace('screen_for_', '')
        for name in globals()
        if name.startswith('screen_for_') and callable(globals()[name])
    ]
    
    return sorted(screener_functions)
