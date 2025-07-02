"""
Stock screener for identifying stocks in sectors experiencing market corrections.

This screener identifies sectors that are in correction (down 10% or more from their
high) and returns stocks from those sectors that may represent buying opportunities.
"""

import pandas as pd
from tqdm import tqdm

from .common import logger
from market_data import get_sector_performances, is_market_in_correction

def screen_for_sector_corrections(universe_df, threshold=-10, market_data=None):
    """
    Screen for stocks in sectors that are currently in correction.
    A sector is considered in correction if it's down at least 10% from its high.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        threshold (float): Percentage threshold for considering a sector in correction (default -10%)
        market_data (dict): Optional pre-loaded market data
        
    Returns:
        DataFrame: Stocks in correcting sectors
    """
    logger.info(f"Screening for stocks in sectors with correction (performance <= {threshold}%)...")
    
    # Get sector performance data (if not already provided)
    if market_data is not None and 'sector_performance' in market_data:
        sector_performance = market_data['sector_performance']
    else:
        sector_performance = get_sector_performances()
    
    # Check if the overall market is in correction
    try:
        market_correction, market_status = is_market_in_correction()
        logger.info(f"Overall market status: {market_status}")
    except Exception as e:
        logger.error(f"Error checking market correction status: {e}")
        market_correction = False
    
    # Filter sectors that are in correction
    sectors_in_correction = sector_performance[sector_performance['performance'] <= threshold]
    
    if len(sectors_in_correction) == 0:
        logger.info("No sectors are currently in correction")
        return pd.DataFrame()
    
    logger.info(f"Found {len(sectors_in_correction)} sectors in correction:")
    for _, row in sectors_in_correction.iterrows():
        logger.info(f"  {row['sector']}: {row['performance']:.2f}%")
    
    # Get list of correcting sector names
    correcting_sectors = sectors_in_correction['sector'].tolist()
    
    # Map gics_sector in universe_df to match sector performance data format
    sector_mapping = {
        'Information Technology': 'Technology',
        'Financials': 'Financial',
        'Health Care': 'Healthcare',
        'Consumer Discretionary': 'Consumer Cyclical',
        'Communication Services': 'Communication Services',
        'Industrials': 'Industrial',
        'Consumer Staples': 'Consumer Defensive',
        'Real Estate': 'Real Estate',
        'Utilities': 'Utilities',
        'Materials': 'Basic Materials',
        'Energy': 'Energy'
    }
    
    # Find stocks in correcting sectors
    results = []
    
    for _, row in tqdm(universe_df.iterrows(), total=len(universe_df), 
                      desc="Screening for stocks in market corrections", unit="stock"):
        symbol = row['symbol']
        sector = row.get('gics_sector', None)
        
        # Map sector if needed
        if sector in sector_mapping:
            sector = sector_mapping[sector]
        
        if sector in correcting_sectors:
            # Get the performance for this sector
            sector_data = sector_performance[sector_performance['sector'] == sector]
            if len(sector_data) > 0:
                performance = sector_data.iloc[0]['performance']
                
                results.append({
                    'symbol': symbol,
                    'company_name': row.get('security', symbol),
                    'sector': sector,
                    'sector_performance': performance,
                    'meets_threshold': True,
                    'reason': f"In correcting sector ({sector}: {performance:.2f}%)"
                })
    
    if not results:
        logger.info("No stocks found in correcting sectors")
        return pd.DataFrame()
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by sector performance (ascending - most corrected sectors first)
    results_df = results_df.sort_values('sector_performance')
    
    logger.info(f"Found {len(results_df)} stocks in correcting sectors")
    return results_df
