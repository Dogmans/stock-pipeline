"""
Pre-Pump Insider Buying Screener
Flags stocks with recent spikes in insider buying activity combined with technical consolidation patterns.

This screener analyzes:
1. Insider buying acceleration (recent vs historical activity)
2. Technical consolidation patterns (price stability, volume analysis)
3. Buying activity strength (acquisitions vs dispositions)
4. Transaction volumes and frequency
5. Insider types and diversity (executives, directors, etc.)
6. Pre-pump technical setup (support levels, low volatility)
"""

import pandas as pd
import logging
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from tqdm import tqdm
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
import config

# Get logger for this module
from utils.logger import get_logger
logger = get_logger(__name__)

def screen_for_insider_buying(universe_df, min_buying_score=65.0, lookback_days=60):
    """
    Screen for stocks with pre-pump insider buying patterns and technical consolidation.
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed
        min_buying_score (float): Minimum pre-pump score (0-100) for meets_threshold flag
        lookback_days (int): Number of days to look back for insider activity
        
    Returns:
        DataFrame: Stocks with pre-pump insider buying patterns, sorted by score
    """
    logger.info(f"Screening for pre-pump insider buying patterns (threshold: {min_buying_score}/100, lookback: {lookback_days} days)...")
    
    # Extract symbols from universe  
    symbols = universe_df['symbol'].tolist()
    
    # Get all recent insider trading data first
    logger.info("Fetching recent insider trading data...")
    insider_data = get_recent_insider_trading(lookback_days)
    
    if not insider_data:
        logger.warning("No insider trading data available")
        return pd.DataFrame()
    
    # Filter to our universe symbols
    universe_symbols = set(symbols)
    relevant_data = [trade for trade in insider_data if trade.get('symbol') in universe_symbols]
    
    logger.info(f"Found {len(relevant_data)} insider trades for {len(set(trade['symbol'] for trade in relevant_data))} symbols in universe")
    
    # Analyze pre-pump patterns for each symbol
    return analyze_pre_pump_patterns(relevant_data, universe_df, min_buying_score, lookback_days)

def get_recent_insider_trading(lookback_days=60):
    """
    Get recent insider trading data from FMP API.
    
    Args:
        lookback_days (int): Number of days to look back
        
    Returns:
        list: List of insider trading records
    """
    provider = FinancialModelingPrepProvider()
    
    try:
        # Use the v4 API for insider trading
        import requests
        api_key = config.FINANCIAL_MODELING_PREP_API_KEY
        
        all_trades = []
        page = 0
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # FMP returns 100 records per call, we'll fetch multiple pages
        while page < 10:  # Limit to prevent infinite loops
            url = f"https://financialmodelingprep.com/api/v4/insider-trading?page={page}&apikey={api_key}"
            
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Error fetching insider trading data: {response.status_code}")
                break
                
            data = response.json()
            if not data:
                break
                
            # Filter by date
            recent_trades = []
            for trade in data:
                try:
                    trade_date = datetime.strptime(trade['transactionDate'], '%Y-%m-%d')
                    if trade_date >= cutoff_date:
                        recent_trades.append(trade)
                except:
                    continue
            
            all_trades.extend(recent_trades)
            
            # If we got fewer than 100 records or no recent trades, we're done
            if len(data) < 100 or not recent_trades:
                break
                
            page += 1
            
        logger.info(f"Retrieved {len(all_trades)} insider trades from last {lookback_days} days")
        return all_trades
        
    except Exception as e:
        logger.error(f"Error fetching insider trading data: {e}")
        return []

def analyze_pre_pump_patterns(insider_data, universe_df, min_buying_score, lookback_days):
    """
    Analyze pre-pump patterns combining insider buying acceleration with technical analysis.
    
    Args:
        insider_data (list): List of insider trading records
        universe_df (DataFrame): Stock universe data
        min_buying_score (float): Minimum score threshold
        lookback_days (int): Lookback period
        
    Returns:
        DataFrame: Analysis results with pre-pump scores
    """
    # Group trades by symbol
    symbol_trades = defaultdict(list)
    for trade in insider_data:
        symbol_trades[trade['symbol']].append(trade)
    
    results = []
    provider = FinancialModelingPrepProvider()
    
    for symbol in tqdm(symbol_trades.keys(), desc="Analyzing pre-pump patterns", unit="symbol"):
        try:
            trades = symbol_trades[symbol]
            
            # Calculate insider buying acceleration and patterns
            insider_analysis = calculate_pre_pump_score(trades, symbol, provider)
            
            if insider_analysis['total_trades'] > 0:
                # Get company info from universe
                company_info = universe_df[universe_df['symbol'] == symbol]
                company_name = company_info['security'].iloc[0] if not company_info.empty else symbol
                sector = company_info['gics_sector'].iloc[0] if not company_info.empty and 'gics_sector' in company_info.columns else 'Unknown'
                
                # Calculate meets_threshold based on pre-pump score
                meets_threshold = insider_analysis['pre_pump_score'] >= min_buying_score
                
                result = {
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'buying_score': insider_analysis['pre_pump_score'],  # Changed to pre_pump_score
                    'total_trades': insider_analysis['total_trades'],
                    'buy_trades': insider_analysis['buy_trades'],
                    'sell_trades': insider_analysis['sell_trades'],
                    'net_shares': insider_analysis['net_shares'],
                    'buy_value': insider_analysis['buy_value'],
                    'sell_value': insider_analysis['sell_value'],
                    'unique_insiders': insider_analysis['unique_insiders'],
                    'executive_trades': insider_analysis['executive_trades'],
                    'director_trades': insider_analysis['director_trades'],
                    'recent_activity_spike': insider_analysis['recent_activity_spike'],
                    'avg_trade_size': insider_analysis['avg_trade_size'],
                    'acceleration_score': insider_analysis['acceleration_score'],
                    'technical_score': insider_analysis['technical_score'],
                    'consolidation_detected': insider_analysis['consolidation_detected'],
                    'volume_pattern_score': insider_analysis['volume_pattern_score'],
                    'meets_threshold': meets_threshold,
                    'reason': f"Pre-pump score: {insider_analysis['pre_pump_score']:.1f}/100" + 
                             (f" - {insider_analysis['buy_trades']} buy trades vs {insider_analysis['sell_trades']} sells" if insider_analysis['total_trades'] > 0 else "") +
                             (f" - Consolidation: {'Yes' if insider_analysis['consolidation_detected'] else 'No'}")
                }
                
                results.append(result)
                
                if meets_threshold:
                    logger.debug(f"Found {symbol} with high pre-pump score: {insider_analysis['pre_pump_score']:.1f}/100")
                    
        except Exception as e:
            logger.error(f"Error analyzing insider buying for {symbol}: {e}")
            continue
    
    # Convert to DataFrame and sort by buying score
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('buying_score', ascending=False)
        logger.info(f"Pre-pump analysis completed. Found {len(df[df['meets_threshold']])} stocks above threshold")
        return df
    else:
        logger.warning("No pre-pump patterns found")
        return pd.DataFrame()

def calculate_pre_pump_score(trades, symbol, provider):
    """
    Calculate pre-pump score combining insider buying acceleration with technical analysis.
    
    Args:
        trades (list): List of trades for a symbol
        symbol (str): Stock symbol
        provider: Data provider for technical analysis
        
    Returns:
        dict: Pre-pump analysis metrics
    """
    if not trades:
        return {
            'pre_pump_score': 0,
            'total_trades': 0,
            'buy_trades': 0,
            'sell_trades': 0,
            'net_shares': 0,
            'buy_value': 0,
            'sell_value': 0,
            'unique_insiders': 0,
            'executive_trades': 0,
            'director_trades': 0,
            'recent_activity_spike': False,
            'avg_trade_size': 0,
            'acceleration_score': 0,
            'technical_score': 0,
            'consolidation_detected': False,
            'volume_pattern_score': 0
        }
    
    # 1. INSIDER BUYING ANALYSIS (40 points max)
    insider_metrics = analyze_insider_activity(trades)
    
    # 2. TECHNICAL ANALYSIS (35 points max)
    technical_metrics = analyze_technical_setup(symbol, provider)
    
    # 3. ACCELERATION ANALYSIS (25 points max)
    acceleration_metrics = analyze_buying_acceleration(trades)
    
    # Combine scores
    insider_score = calculate_insider_component_score(insider_metrics)
    technical_score = technical_metrics['score']
    acceleration_score = acceleration_metrics['score']
    
    pre_pump_score = min(100, insider_score + technical_score + acceleration_score)
    
    return {
        'pre_pump_score': pre_pump_score,
        'total_trades': insider_metrics['total_trades'],
        'buy_trades': insider_metrics['buy_trades'],
        'sell_trades': insider_metrics['sell_trades'],
        'net_shares': insider_metrics['net_shares'],
        'buy_value': insider_metrics['buy_value'],
        'sell_value': insider_metrics['sell_value'],
        'unique_insiders': insider_metrics['unique_insiders'],
        'executive_trades': insider_metrics['executive_trades'],
        'director_trades': insider_metrics['director_trades'],
        'recent_activity_spike': acceleration_metrics['recent_spike'],
        'avg_trade_size': insider_metrics['avg_trade_size'],
        'acceleration_score': acceleration_score,
        'technical_score': technical_score,
        'consolidation_detected': technical_metrics['consolidation_detected'],
        'volume_pattern_score': technical_metrics['volume_score']
    }

def analyze_insider_activity(trades):
    """Analyze basic insider trading activity patterns."""
    buy_trades = []
    sell_trades = []
    unique_insiders = set()
    executive_trades = 0
    director_trades = 0
    
    for trade in trades:
        # Track unique insiders
        unique_insiders.add(trade.get('reportingName', ''))
        
        # Categorize by insider type
        owner_type = trade.get('typeOfOwner', '').lower()
        if 'officer' in owner_type or 'ceo' in owner_type or 'cfo' in owner_type:
            executive_trades += 1
        elif 'director' in owner_type:
            director_trades += 1
        
        # Categorize by transaction type - FIXED METHODOLOGY
        acquisition = trade.get('acquistionOrDisposition', '').upper()
        transaction_type = trade.get('transactionType', '').upper()
        
        # Only consider ACTUAL PURCHASES with real money as buying signals:
        # - A-P-Purchase: Open market purchases with personal money
        # - Only transactions with price > 0 (exclude $0 option exercises)
        price = trade.get('price', 0)
        
        if (acquisition == 'A' and 
            ('PURCHASE' in transaction_type or 
             'BUY' in transaction_type)):
            # Must have actual price paid (not $0 option exercises)
            if price > 0 and not ('AWARD' in transaction_type or 'GRANT' in transaction_type):
                buy_trades.append(trade)
        elif (acquisition == 'D' and 
              ('SALE' in transaction_type or 
               'SELL' in transaction_type)):
            sell_trades.append(trade)
    
    # Calculate trade values
    buy_value = sum(trade.get('securitiesTransacted', 0) * trade.get('price', 0) for trade in buy_trades)
    sell_value = sum(trade.get('securitiesTransacted', 0) * trade.get('price', 0) for trade in sell_trades)
    net_shares = sum(trade.get('securitiesTransacted', 0) for trade in buy_trades) - sum(trade.get('securitiesTransacted', 0) for trade in sell_trades)
    
    total_trades = len(trades)
    avg_trade_size = (buy_value + sell_value) / total_trades if total_trades > 0 else 0
    
    return {
        'total_trades': total_trades,
        'buy_trades': len(buy_trades),
        'sell_trades': len(sell_trades),
        'net_shares': net_shares,
        'buy_value': buy_value,
        'sell_value': sell_value,
        'unique_insiders': len(unique_insiders),
        'executive_trades': executive_trades,
        'director_trades': director_trades,
        'avg_trade_size': avg_trade_size
    }

def calculate_insider_component_score(metrics):
    """Calculate insider activity component score (0-40 points)."""
    score = 0
    
    # Buy vs sell ratio (0-25 points)
    if metrics['total_trades'] > 0:
        buy_ratio = metrics['buy_trades'] / metrics['total_trades']
        score += buy_ratio * 25
    
    # Net buying activity (0-10 points)
    if metrics['net_shares'] > 0:
        score += min(10, metrics['net_shares'] / 10000)
    
    # Insider diversity (0-5 points)
    if metrics['unique_insiders'] > 1:
        score += min(5, metrics['unique_insiders'])
    
    return min(40, score)

def analyze_buying_acceleration(trades):
    """Analyze acceleration in buying activity (0-25 points)."""
    if not trades:
        return {'score': 0, 'recent_spike': False}
    
    # Split trades into recent (30 days) vs older periods
    recent_cutoff = datetime.now() - timedelta(days=30)
    recent_trades = []
    older_trades = []
    
    for trade in trades:
        try:
            trade_date = datetime.strptime(trade['transactionDate'], '%Y-%m-%d')
            if trade_date >= recent_cutoff:
                recent_trades.append(trade)
            else:
                older_trades.append(trade)
        except:
            continue
    
    score = 0
    recent_spike = False
    
    # Recent activity acceleration (0-15 points)
    if len(older_trades) > 0:
        acceleration_ratio = len(recent_trades) / len(older_trades)
        if acceleration_ratio > 1.5:  # 50% more recent activity
            score += min(15, acceleration_ratio * 5)
            recent_spike = True
    elif len(recent_trades) >= 2:  # No historical data but recent activity
        score += 10
        recent_spike = True
    
    # Recent volume surge (0-10 points)
    recent_buy_count = sum(1 for trade in recent_trades 
                          if trade.get('acquistionOrDisposition', '').upper() == 'A')
    if recent_buy_count >= 2:
        score += min(10, recent_buy_count * 2)
    
    return {'score': min(25, score), 'recent_spike': recent_spike}

def analyze_technical_setup(symbol, provider):
    """Analyze technical consolidation patterns (0-35 points)."""
    try:
        # Get 90 days of price data for technical analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Get historical price data
        price_data = provider.get_historical_prices(
            symbol, 
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d')
        )
        
        if not price_data or len(price_data) < 30:
            return {'score': 0, 'consolidation_detected': False, 'volume_score': 0}
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(price_data)
        if 'close' not in df.columns:
            return {'score': 0, 'consolidation_detected': False, 'volume_score': 0}
        
        # Calculate consolidation score (0-20 points)
        consolidation_score, consolidation_detected = calculate_consolidation_score(df)
        
        # Calculate volume pattern score (0-15 points)
        volume_score = calculate_volume_pattern_score(df)
        
        total_technical_score = min(35, consolidation_score + volume_score)
        
        return {
            'score': total_technical_score,
            'consolidation_detected': consolidation_detected,
            'volume_score': volume_score
        }
        
    except Exception as e:
        logger.debug(f"Technical analysis failed for {symbol}: {e}")
        return {'score': 0, 'consolidation_detected': False, 'volume_score': 0}

def calculate_consolidation_score(df):
    """Calculate price consolidation score."""
    try:
        # Calculate 30-day rolling volatility
        df['returns'] = df['close'].pct_change()
        recent_volatility = df['returns'].tail(30).std() * np.sqrt(252)  # Annualized
        
        # Low volatility indicates consolidation
        if recent_volatility < 0.15:  # Less than 15% annualized volatility
            consolidation_score = max(0, 20 - (recent_volatility * 100))
            return consolidation_score, True
        else:
            return 0, False
            
    except Exception:
        return 0, False

def calculate_volume_pattern_score(df):
    """Calculate volume pattern score."""
    try:
        if 'volume' not in df.columns:
            return 0
        
        # Calculate average volume over different periods
        recent_volume = df['volume'].tail(10).mean()
        historical_volume = df['volume'].mean()
        
        # Higher recent volume relative to historical average
        if recent_volume > historical_volume * 1.2:
            volume_ratio = recent_volume / historical_volume
            return min(15, volume_ratio * 5)
        
        return 0
        
    except Exception:
        return 0
