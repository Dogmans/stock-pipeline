"""
Configuration settings for the stock screening pipeline.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys - set these in your environment or .env file
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
FINANCIAL_MODELING_PREP_API_KEY = os.getenv('FINANCIAL_MODELING_PREP_API_KEY')

# Screening Parameters
class ScreeningThresholds:
    # Book Value Parameters
    MAX_PRICE_TO_BOOK_RATIO = 1.2  # Look for stocks trading near or below book value
    
    # P/E Ratio Parameters
    MAX_PE_RATIO = 10  # As recommended by Graham/Buffett
    MAX_FORWARD_PE_RATIO = 15  # Slightly higher for growth stocks
    
    # 52-Week Low Parameters
    MIN_PERCENT_OFF_52_WEEK_LOW = 0  # Currently at 52-week low
    MAX_PERCENT_OFF_52_WEEK_LOW = 15  # Within 15% of 52-week low
    MIN_YEAR_TO_DATE_DECLINE = 75  # Look for stocks that have dropped 75%+ YTD (for big rebounds)
    
    # Debt Parameters
    MAX_DEBT_TO_EQUITY = 0.5  # Conservative debt level
    MAX_DEBT_TO_EBITDA = 3.0  # Conservative debt level
    
    # Cash Runway (for unprofitable companies)
    MIN_CASH_RUNWAY_MONTHS = 18  # At least 18 months of cash left at current burn rate
    
    # Biotech/Unprofitable Company Special Case
    BIOTECH_MIN_CASH_TO_MARKET_CAP = 0.8  # Cash at least 80% of market cap (deep value)
    
    # Volume Requirements
    MIN_AVERAGE_VOLUME = 100000  # Ensure sufficient liquidity
    
    # Market Cap Requirements (in millions)
    MIN_MARKET_CAP = 100  # Small caps and up (no micro caps)
    MAX_MARKET_CAP = None  # No upper limit

# Market Indexes to Track
MARKET_INDEXES = [
    '^GSPC',  # S&P 500
    '^DJI',   # Dow Jones Industrial
    '^IXIC',  # NASDAQ
    '^RUT',   # Russell 2000
]

# Sector ETFs to Track
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLV': 'Healthcare',
    'IBB': 'Biotech',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLI': 'Industrials',
    'XLB': 'Materials',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
}

# VIX Thresholds
VIX_BLACK_SWAN_THRESHOLD = 50  # VIX level indicating a potential black swan event
VIX_CORRECTION_THRESHOLD = 30  # VIX level indicating market correction

# Alert Settings
EMAIL_ALERTS = False  # Set to True to enable email alerts
EMAIL_RECIPIENT = ""  # Your email address for alerts
DAILY_REPORT_TIME = "08:00"  # Time for daily summary report

# File Paths
DATA_DIR = "data"
RESULTS_DIR = "results"
OUTPUT_DIR = "output"

# Universe of stocks to screen
UNIVERSES = {
    "SP500": "sp500",
    "RUSSELL2000": "russell2000",
    "NASDAQ100": "nasdaq100",
    "ALL": "all"
}

# Default universe to screen
DEFAULT_UNIVERSE = UNIVERSES["SP500"]

# Data cache settings
CACHE_EXPIRY_HOURS = 24  # Refresh data every 24 hours
