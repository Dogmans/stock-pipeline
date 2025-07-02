"""
Test script for the sector corrections screener
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add the project directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

# Import project modules
from screeners.sector_corrections import screen_for_sector_corrections
from utils.logger import get_logger

# Setup logger
logger = get_logger(__name__)

def test_sector_corrections():
    """Test the sector corrections screener with mock data"""
    logger.info("Testing sector corrections screener with mock data...")
    
    # Create mock sector performance data
    df = pd.DataFrame({
        'sector': ['Technology', 'Energy', 'Health Care', 'Financials'],
        '1_month_change': [-12.5, -15.2, -8.3, -21.5]
    })
    
    # Mark sectors in correction
    df['is_correction'] = df['1_month_change'] <= -10.0
    df['is_bear_market'] = df['1_month_change'] <= -20.0
    
    logger.info(f"Created test data with {len(df[df['is_correction']])} sectors in correction")
    
    try:
        # Run the screener with our mock data
        results = screen_for_sector_corrections(market_data={'sector_performance': df})
        
        if not results.empty:
            logger.info(f"Results have {len(results)} rows")
            logger.info(f"Symbol column exists: {'symbol' in results.columns}")
            logger.info(f"Sector column exists: {'sector' in results.columns}")
            
            if 'symbol' in results.columns and 'sector' in results.columns:
                logger.info(f"Sectors in results: {results['sector'].unique().tolist()}")
                logger.info(f"First few symbols: {results['symbol'].head().tolist()}")
        else:
            logger.warning("Results are empty - no stocks in correcting sectors")
    except Exception as e:
        logger.error(f"Error testing sector corrections: {e}")

if __name__ == "__main__":
    test_sector_corrections()
