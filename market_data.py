"""
market_data.py - Market-level data collection functions.

This module provides functions for gathering market-level data, including:
- Market index values and history
- VIX data for measuring market fear
- Sector performance metrics

Functions:
    get_market_conditions(): Fetch current market conditions including indexes and VIX
    is_market_in_correction(): Determine if the market is in a correction based on VIX
    get_sector_performances(): Calculate performance metrics for market sectors
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
from datetime import datetime, timedelta

import config
from utils.logger import get_logger
from cache_manager import cache_api_call

# Get logger for this module
logger = get_logger(__name__)

@cache_api_call(expiry_hours=6, cache_key_prefix="market_conditions")
def get_market_conditions(data_provider=None, force_refresh=False):
    """
    Fetch current market conditions, including index values and VIX.
    
    Downloads historical data for major market indexes and the VIX to assess
    the current market environment.
    
    Args:
        data_provider: Data provider object to use for fetching data
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        dict: Dictionary with market condition data, containing DataFrames
             for each market index and the VIX
    """
    market_data = {}
    
    try:
        # Import the data provider modules if not provided
        if data_provider is None:
            # For index data, use YFinance provider specifically as it works best with market indexes
            from data_providers.yfinance_provider import YFinanceProvider
            yf_provider = YFinanceProvider()
            logger.info(f"Using YFinance provider for market index data")
            
            # For sector ETF data, use Financial Modeling Prep as preferred provider
            from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
            fmp_provider = FinancialModelingPrepProvider()
            logger.info(f"Using Financial Modeling Prep provider for sector ETF data")
        else:
            # If a specific provider is requested, use it for both
            yf_provider = data_provider
            fmp_provider = data_provider
            
        # Get data for market indexes - YFinance tends to be most reliable for these
        indexes_data = yf_provider.get_historical_prices(
            config.MARKET_INDEXES, 
            period="1y", 
            interval="1d",
            force_refresh=force_refresh
        )
        
        for index in config.MARKET_INDEXES:
            if index in indexes_data:
                market_data[index] = indexes_data[index]
        
        # Get VIX data - YFinance tends to be most reliable for VIX
        vix_data = yf_provider.get_historical_prices(
            ["^VIX"], 
            period="1y", 
            interval="1d",
            force_refresh=force_refresh
        )
        if "^VIX" in vix_data:
            market_data['VIX'] = vix_data["^VIX"]
        
        # Get sector ETF data - Use FMP for ETFs since we have a paid subscription
        sector_etfs = list(config.SECTOR_ETFS.keys())
        etf_data = fmp_provider.get_historical_prices(
            sector_etfs, 
            period="1y", 
            interval="1d",
            force_refresh=force_refresh
        )
        
        for etf in sector_etfs:
            if etf in etf_data:
                market_data[etf] = etf_data[etf]
        
        logger.info(f"Successfully retrieved market data for {len(market_data)} indexes/ETFs")
        
    except Exception as e:
        logger.error(f"Error fetching market conditions: {e}")
    
    return market_data

@cache_api_call(expiry_hours=6, cache_key_prefix="market_correction")
def is_market_in_correction(data_provider=None, force_refresh=False):
    """
    Determine if the market is in a correction or crash based on VIX levels.
    
    VIX level thresholds are defined in config.py:
    - VIX >= VIX_BLACK_SWAN_THRESHOLD indicates a major market event
    - VIX >= VIX_CORRECTION_THRESHOLD indicates a market correction
    
    Args:
        data_provider: Data provider object to use for fetching data
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        tuple: (bool, str) - Is in correction state and description
    """
    try:
        # Import the data provider module if not provided
        if data_provider is None:
            import data_providers
            data_provider = data_providers.get_provider()
            logger.info(f"Using default data provider for VIX data: {data_provider.get_provider_name()}")        # Get latest VIX value
        vix_data = data_provider.get_historical_prices(
            ["^VIX"], 
            period="5d", 
            interval="1d",
            force_refresh=force_refresh
        )
        
        latest_vix = None
        
        if "^VIX" in vix_data:
            df = vix_data["^VIX"]
            
            # Handle different DataFrame structures that could be returned
            try:
                # Case 1: Standard DataFrame with 'Close' as a column
                if 'Close' in df.columns and not isinstance(df.columns, pd.MultiIndex):
                    latest_vix = df['Close'].iloc[-1]
                    logger.info(f"Retrieved VIX from standard DataFrame structure: {latest_vix}")
                
                # Case 2: MultiIndex columns with ('Ticker', 'Price') format
                elif isinstance(df.columns, pd.MultiIndex):
                    # Identify which level contains 'Close'
                    levels = [df.columns.get_level_values(i) for i in range(df.columns.nlevels)]
                    
                    # If 'Close' is in any level
                    for i, level in enumerate(levels):
                        if 'Close' in level:
                            # Get all columns where this level has value 'Close'
                            close_cols = [col for col in df.columns if col[i] == 'Close']
                            if close_cols:
                                latest_vix = df[close_cols[0]].iloc[-1]
                                logger.info(f"Retrieved VIX from MultiIndex columns: {latest_vix}")
                                break
                
                # Case 3: Last row might contain Close in MultiIndex
                if latest_vix is None:
                    last_row = df.iloc[-1]
                    if isinstance(last_row.index, pd.MultiIndex):
                        # If MultiIndex has 'Close' in it
                        for i in range(last_row.index.nlevels):
                            if 'Close' in last_row.index.get_level_values(i):
                                # This level contains 'Close', find the position
                                for j, idx in enumerate(last_row.index):
                                    if isinstance(idx, tuple) and 'Close' in idx:
                                        latest_vix = last_row.iloc[j]
                                        logger.info(f"Retrieved VIX from MultiIndex rows: {latest_vix}")
                                        break
                    # Handle case shown in last request where 'Close' is in the index
                    elif hasattr(last_row, 'Close'):
                        latest_vix = last_row.Close
                        logger.info(f"Retrieved VIX from last_row.Close: {latest_vix}")
                    elif 'Close' in last_row.index:
                        latest_vix = last_row['Close']
                        logger.info(f"Retrieved VIX from last_row['Close']: {latest_vix}")
                        
                # Case 4: Using xs() method to access MultiIndex
                if latest_vix is None and isinstance(last_row.index, pd.MultiIndex):
                    try:
                        latest_vix = df.xs('Close', level=1, axis=1).iloc[-1]
                        logger.info(f"Retrieved VIX using xs() method: {latest_vix}")
                    except:
                        pass
            
            except Exception as inner_e:
                logger.error(f"Failed to extract Close price from VIX data: {inner_e}")
                # Print the structure of the DataFrame to help diagnose issues
                try:
                    if not df.empty:
                        logger.info(f"VIX data structure - columns: {df.columns}")
                        logger.info(f"VIX data structure - last row index: {type(df.iloc[-1].index)}")
                except:
                    pass
        
        # If we were unable to extract VIX data by any method
        if latest_vix is None:
            # Try with 'VIX' symbol without caret as fallback
            try:
                fallback_data = data_provider.get_historical_prices(
                    ["VIX"], 
                    period="5d", 
                    interval="1d",
                    force_refresh=force_refresh
                )
                
                if "VIX" in fallback_data and not fallback_data["VIX"].empty:
                    df = fallback_data["VIX"]
                    if 'Close' in df.columns:
                        latest_vix = df['Close'].iloc[-1]
                        logger.info(f"Retrieved VIX using fallback symbol without caret: {latest_vix}")
            except Exception as fallback_e:
                logger.error(f"Fallback VIX retrieval failed: {fallback_e}")
        
        # If we still don't have VIX data, return error
        if latest_vix is None:
            logger.error("Could not retrieve VIX data using any available method")
            return False, "Error: Could not retrieve market status"
            
            if latest_vix >= config.VIX_BLACK_SWAN_THRESHOLD:
                logger.info(f"Market is in Black Swan territory (VIX: {latest_vix:.2f})")
                return True, f"Black Swan Event (VIX: {latest_vix:.2f})"
            elif latest_vix >= config.VIX_CORRECTION_THRESHOLD:
                logger.info(f"Market is in correction territory (VIX: {latest_vix:.2f})")
                return True, f"Market Correction (VIX: {latest_vix:.2f})"
            else:
                logger.info(f"Normal market conditions (VIX: {latest_vix:.2f})")
                return False, f"Normal Market Conditions (VIX: {latest_vix:.2f})"
        else:
            logger.error("Could not retrieve VIX data")
            return False, "Error: Could not retrieve market status"
            
    except Exception as e:
        logger.error(f"Error checking market correction status: {e}")
        return False, "Unknown (Error fetching data)"

@cache_api_call(expiry_hours=6, cache_key_prefix="sector_performances")
def get_sector_performances(data_provider=None, force_refresh=False):
    """
    Calculate the performance of different market sectors.
    
    Analyzes the performance of sector ETFs to identify sector-specific
    trends, corrections, and opportunities.
    
    Args:
        data_provider: Data provider object to use for fetching data
        force_refresh (bool, optional): If True, bypass cache and fetch fresh data
    
    Returns:
        DataFrame: DataFrame with sector performance data, including:
                  - ETF symbol
                  - Sector name
                  - Current price
                  - 1-week, 1-month, 3-month, and YTD percentage changes
    """
    try:
        # Import the data provider module if not provided
        if data_provider is None:
            import data_providers
            data_provider = data_providers.get_provider()
            logger.info(f"Using default data provider for sector data: {data_provider.get_provider_name()}")
            
        sector_etfs = list(config.SECTOR_ETFS.keys())
        etf_data = data_provider.get_historical_prices(
            sector_etfs, 
            period="1y", 
            interval="1d",
            force_refresh=force_refresh
        )
        
        results = []
        for etf in sector_etfs:
            if etf in etf_data:
                data = etf_data[etf]
                
                if data.empty:
                    continue
                
                # Calculate 1-week, 1-month, 3-month, and YTD changes
                current_price = data['Close'].iloc[-1]
                week_ago_price = data['Close'].iloc[-6] if len(data) >= 6 else data['Close'].iloc[0]
                month_ago_price = data['Close'].iloc[-22] if len(data) >= 22 else data['Close'].iloc[0]
                three_month_ago_price = data['Close'].iloc[-66] if len(data) >= 66 else data['Close'].iloc[0]
                
                # Find start of year price
                start_of_year = data[data.index.year == data.index[0].year].iloc[0]['Close']
                
                # Calculate percentage changes
                week_change = ((current_price / week_ago_price) - 1) * 100
                month_change = ((current_price / month_ago_price) - 1) * 100
                three_month_change = ((current_price / three_month_ago_price) - 1) * 100
                ytd_change = ((current_price / start_of_year) - 1) * 100
                
                results.append({
                    'etf': etf,
                    'sector': config.SECTOR_ETFS[etf],
                    'price': current_price,
                    '1_week_change': week_change,
                    '1_month_change': month_change,
                    '3_month_change': three_month_change,
                    'ytd_change': ytd_change
                })
                
        if results:
            df = pd.DataFrame(results)
            # Sort by 1-month performance from worst to best (for finding downtrodden sectors)
            df = df.sort_values('1_month_change')
            logger.info(f"Calculated performance for {len(df)} sector ETFs")
            return df
        else:
            logger.warning("No sector ETF data retrieved")
            return pd.DataFrame(columns=['etf', 'sector', 'price', '1_week_change', '1_month_change', '3_month_change', 'ytd_change'])
            
    except Exception as e:
        logger.error(f"Error calculating sector performances: {e}")
        return pd.DataFrame(columns=['etf', 'sector', 'price', '1_week_change', '1_month_change', '3_month_change', 'ytd_change'])

if __name__ == "__main__":
    # Test module functionality
    logger.info("Testing market data module...")
    
    # Get the data provider
    import data_providers
    data_provider = data_providers.get_provider()
    logger.info(f"Using data provider: {data_provider.get_provider_name()}")
    
    # Test market conditions
    market_data = get_market_conditions(data_provider=data_provider)
    logger.info(f"Fetched market data for {len(market_data)} indexes/ETFs")
    
    # Test VIX correction check
    in_correction, status = is_market_in_correction(data_provider=data_provider)
    logger.info(f"Market status: {status}")
    
    # Test sector performance
    sectors = get_sector_performances(data_provider=data_provider)
    if not sectors.empty:
        logger.info(f"Top underperforming sector: {sectors.iloc[0]['sector']} ({sectors.iloc[0]['1_month_change']:.2f}%)")
        logger.info(f"Top outperforming sector: {sectors.iloc[-1]['sector']} ({sectors.iloc[-1]['1_month_change']:.2f}%)")
    
    logger.info("Market data module test complete")
