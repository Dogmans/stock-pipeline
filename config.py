"""
Configuration settings for the stock screening pipeline.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

LOGLEVEL = os.getenv('LOGLEVEL', 'DEBUG').upper()  # Default to DEBUG if not set

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
    
    # Sharpe Ratio Parameters
    MIN_SHARPE_RATIO = 1.0  # Minimum Sharpe ratio for risk-adjusted returns
    
    # Momentum Parameters
    MIN_MOMENTUM_SCORE = 15.0  # Minimum momentum score (%) for 6-month/3-month weighted average
    
    # Quality Parameters
    MIN_QUALITY_SCORE = 6.0  # Minimum quality score (out of 10) based on financial strength
    
    # Enhanced Quality Parameters (0-100 point scale)
    MIN_ENHANCED_QUALITY_SCORE = 50.0  # Minimum enhanced quality score (out of 100)
    # Component thresholds for enhanced quality (each 0-25 points):
    MIN_ROE_COMPONENT_SCORE = 8.0       # Minimum ROE component score
    MIN_PROFITABILITY_COMPONENT_SCORE = 10.0  # Minimum profitability component score  
    MIN_FINANCIAL_STRENGTH_COMPONENT_SCORE = 12.0  # Minimum financial strength component score
    MIN_GROWTH_QUALITY_COMPONENT_SCORE = 8.0  # Minimum growth quality component score
    
    # Free Cash Flow Yield Parameters
    MIN_FCF_YIELD = 3.5  # Minimum free cash flow yield (%) relative to market cap
    
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
    
    # Quarters for analysis
    QUARTERS_RETURNED = 6

class CombinedScreeners:
    """
    Configuration for multiple combined screeners.
    Each combined screener can have its own set of strategies.
    """
    
    # Traditional Value Investing Combined Screener
    TRADITIONAL_VALUE = {
        'name': 'Traditional Value',
        'description': 'Classic value investing metrics (P/E, P/B, PEG)',
        'strategies': ['pe_ratio', 'price_to_book', 'peg_ratio']
    }
    
    # High Performance Combined Screener (Research-Based)
    HIGH_PERFORMANCE = {
        'name': 'High Performance',
        'description': 'Research-backed high-performance metrics (Momentum, Quality, FCF Yield)',
        'strategies': ['momentum', 'quality', 'free_cash_flow_yield']
    }
    
    # Comprehensive Combined Screener
    COMPREHENSIVE = {
        'name': 'Comprehensive',
        'description': 'All available screening strategies combined',
        'strategies': ['pe_ratio', 'price_to_book', 'peg_ratio', 'momentum', 'quality', 'free_cash_flow_yield', 'sharpe_ratio']
    }
    
    # Distressed/Turnaround Combined Screener
    DISTRESSED_VALUE = {
        'name': 'Distressed Value',
        'description': 'Stocks near lows with turnaround potential',
        'strategies': ['52_week_lows', 'fallen_ipos', 'turnaround_candidates']
    }
    
    @classmethod
    def get_all_combinations(cls):
        """Get all available combined screener configurations."""
        return {
            'traditional_value': cls.TRADITIONAL_VALUE,
            'high_performance': cls.HIGH_PERFORMANCE,
            'comprehensive': cls.COMPREHENSIVE,
            'distressed_value': cls.DISTRESSED_VALUE
        }
    
    @classmethod
    def get_combination(cls, name):
        """Get a specific combined screener configuration by name."""
        combinations = cls.get_all_combinations()
        return combinations.get(name)

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

# API Rate Limits (calls per minute)
API_RATE_LIMITS = {
    "alpha_vantage": 5,      # Alpha Vantage free tier: 5 calls per minute
    "financial_modeling_prep": 300,  # Financial Modeling Prep paid tier: 300 calls per minute
    "finnhub": 60,           # Finnhub free tier: 60 calls per minute
    "yfinance": 2000         # YFinance approximate limit: 2000 calls per minute
}

# API Daily Limits (calls per day)
API_DAILY_LIMITS = {
    "alpha_vantage": 500,    # Alpha Vantage free tier: 500 calls per day
    "financial_modeling_prep": None, # Financial Modeling Prep paid tier: No daily limit
    "finnhub": 60 * 60 * 16  # Finnhub free tier: ~60 calls per minute * 16 hours
}
