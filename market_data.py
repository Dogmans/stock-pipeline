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
from utils import setup_logging

# Set up logger for this module
logger = setup_logging()

def get_market_conditions():
    """
    Fetch current market conditions, including index values and VIX.
    
    Downloads historical data for major market indexes and the VIX to assess
    the current market environment.
    
    Returns:
        dict: Dictionary with market condition data, containing DataFrames
             for each market index and the VIX
    """
    market_data = {}
    
    try:
        # Get data for market indexes
        indexes_data = yf.download(config.MARKET_INDEXES, period="1y", interval="1d", group_by="ticker", progress=False)
        
        for index in config.MARKET_INDEXES:
            if (index,) in indexes_data.columns.levels[0]:
                market_data[index] = indexes_data[index].copy()
        
        # Get VIX data
        vix_data = yf.download("^VIX", period="1y", interval="1d", progress=False)
        market_data['VIX'] = vix_data
        
        # Get sector ETF data
        sector_etfs = list(config.SECTOR_ETFS.keys())
        etf_data = yf.download(sector_etfs, period="1y", interval="1d", group_by="ticker", progress=False)
        
        for etf in sector_etfs:
            if (etf,) in etf_data.columns.levels[0]:
                market_data[etf] = etf_data[etf].copy()
        
        logger.info(f"Successfully retrieved market data for {len(market_data)} indexes/ETFs")
        
    except Exception as e:
        logger.error(f"Error fetching market conditions: {e}")
    
    return market_data

def is_market_in_correction():
    """
    Determine if the market is in a correction or crash based on VIX levels.
    
    VIX level thresholds are defined in config.py:
    - VIX >= VIX_BLACK_SWAN_THRESHOLD indicates a major market event
    - VIX >= VIX_CORRECTION_THRESHOLD indicates a market correction
    
    Returns:
        tuple: (bool, str) - Is in correction state and description
    """
    try:
        # Get latest VIX value
        vix_data = yf.download("^VIX", period="5d", interval="1d", progress=False)
        latest_vix = vix_data['Close'].iloc[-1]
        
        if latest_vix >= config.VIX_BLACK_SWAN_THRESHOLD:
            logger.info(f"Market is in Black Swan territory (VIX: {latest_vix:.2f})")
            return True, f"Black Swan Event (VIX: {latest_vix:.2f})"
        elif latest_vix >= config.VIX_CORRECTION_THRESHOLD:
            logger.info(f"Market is in correction territory (VIX: {latest_vix:.2f})")
            return True, f"Market Correction (VIX: {latest_vix:.2f})"
        else:
            logger.info(f"Normal market conditions (VIX: {latest_vix:.2f})")
            return False, f"Normal Market Conditions (VIX: {latest_vix:.2f})"
            
    except Exception as e:
        logger.error(f"Error checking market correction status: {e}")
        return False, "Unknown (Error fetching data)"

def get_sector_performances():
    """
    Calculate the performance of different market sectors.
    
    Analyzes the performance of sector ETFs to identify sector-specific
    trends, corrections, and opportunities.
    
    Returns:
        DataFrame: DataFrame with sector performance data, including:
                  - ETF symbol
                  - Sector name
                  - Current price
                  - 1-week, 1-month, 3-month, and YTD percentage changes
    """
    try:
        sector_etfs = list(config.SECTOR_ETFS.keys())
        etf_data = yf.download(sector_etfs, period="1y", interval="1d", group_by="ticker", progress=False)
        
        results = []
        for etf in sector_etfs:
            if (etf,) in etf_data.columns.levels[0]:
                data = etf_data[etf].copy()
                
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
    
    # Test market conditions
    market_data = get_market_conditions()
    logger.info(f"Fetched market data for {len(market_data)} indexes/ETFs")
    
    # Test VIX correction check
    in_correction, status = is_market_in_correction()
    logger.info(f"Market status: {status}")
    
    # Test sector performance
    sectors = get_sector_performances()
    if not sectors.empty:
        logger.info(f"Top underperforming sector: {sectors.iloc[0]['sector']} ({sectors.iloc[0]['1_month_change']:.2f}%)")
        logger.info(f"Top outperforming sector: {sectors.iloc[-1]['sector']} ({sectors.iloc[-1]['1_month_change']:.2f}%)")
    
    logger.info("Market data module test complete")
