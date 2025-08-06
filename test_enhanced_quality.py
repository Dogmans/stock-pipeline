"""
Test script for the enhanced quality screener.
Tests the enhanced quality screener with a small sample of stocks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from screeners.enhanced_quality import enhanced_quality_screener, calculate_enhanced_quality_statistics
from config import ScreeningThresholds
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_quality_screener():
    """Test the enhanced quality screener with a sample of stocks."""
    
    # Test with a small sample of well-known stocks
    test_symbols = [
        'AAPL',  # Apple - should score high
        'MSFT',  # Microsoft - should score high  
        'GOOGL', # Google - should score high
        'BRK.B', # Berkshire Hathaway - should score high
        'JNJ',   # Johnson & Johnson - should score high
        'WMT',   # Walmart - should score well
        'PG',    # Procter & Gamble - should score well
        'KO',    # Coca-Cola - should score well
        'V',     # Visa - should score very high
        'MA',    # Mastercard - should score very high
    ]
    
    logger.info(f"Testing enhanced quality screener with {len(test_symbols)} stocks")
    
    # Run the enhanced quality screener
    try:
        # Test with default minimum score (60.0)
        results_df = enhanced_quality_screener(test_symbols, min_quality_score=ScreeningThresholds.MIN_ENHANCED_QUALITY_SCORE)
        
        if results_df.empty:
            logger.warning("No results returned from enhanced quality screener")
            return
            
        logger.info(f"Enhanced quality screening completed. Found {len(results_df)} stocks with data.")
        
        # Calculate statistics
        stats = calculate_enhanced_quality_statistics(results_df)
        
        logger.info("Enhanced Quality Score Statistics:")
        logger.info(f"  Total stocks analyzed: {stats.get('total_stocks', 0)}")
        logger.info(f"  Mean score: {stats.get('mean_score', 0):.1f}")
        logger.info(f"  Median score: {stats.get('median_score', 0):.1f}")
        logger.info(f"  Standard deviation: {stats.get('std_dev', 0):.1f}")
        logger.info(f"  Min score: {stats.get('min_score', 0):.1f}")
        logger.info(f"  Max score: {stats.get('max_score', 0):.1f}")
        logger.info(f"  Top 10% threshold: {stats.get('top_10_percent_threshold', 0):.1f}")
        logger.info(f"  Scores >= 80: {stats.get('scores_above_80', 0)}")
        logger.info(f"  Scores >= 70: {stats.get('scores_above_70', 0)}")
        logger.info(f"  Scores >= 60: {stats.get('scores_above_60', 0)}")
        
        # Show top 5 results
        logger.info("\nTop 5 Enhanced Quality Stocks:")
        top_5 = results_df.head(5)
        for idx, row in top_5.iterrows():
            logger.info(f"  {row['symbol']} ({row['company_name'][:30]}...): {row['enhanced_quality_score']:.0f}/100")
            logger.info(f"    Components - ROE:{row['roe_score']}, Prof:{row['profitability_score']}, Fin:{row['financial_strength_score']}, Growth:{row['growth_quality_score']}")
            
        # Show stocks that meet the threshold
        meets_threshold = results_df[results_df['meets_threshold'] == True]
        logger.info(f"\nStocks meeting threshold (>= {ScreeningThresholds.MIN_ENHANCED_QUALITY_SCORE}):")
        for idx, row in meets_threshold.iterrows():
            logger.info(f"  {row['symbol']}: {row['enhanced_quality_score']:.0f}/100")
            
        # Test with a lower threshold to see more results
        logger.info(f"\nTesting with lower threshold (50.0):")
        results_low_threshold = enhanced_quality_screener(test_symbols, min_quality_score=50.0)
        meets_low_threshold = results_low_threshold[results_low_threshold['meets_threshold'] == True]
        logger.info(f"Stocks meeting lower threshold (>= 50.0): {len(meets_low_threshold)}")
        
        return results_df
        
    except Exception as e:
        logger.error(f"Error testing enhanced quality screener: {e}")
        raise

if __name__ == "__main__":
    test_enhanced_quality_screener()
