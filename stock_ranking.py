"""
stock_ranking.py - Utility for ranking stocks based on various metrics

This module provides functions to rank and sort stocks based on 
strategy-specific metrics to help identify the best candidates.
"""

import pandas as pd
import numpy as np

def rank_stocks(screening_results):
    """
    Rank stocks within each screening strategy based on relevant metrics.
    
    Args:
        screening_results: Dictionary of DataFrames with screening results by strategy
        
    Returns:
        Dictionary of DataFrames with added ranking columns
    """
    ranked_results = {}
    
    for strategy, results in screening_results.items():
        if not isinstance(results, pd.DataFrame) or results.empty:
            ranked_results[strategy] = results
            continue
            
        df = results.copy()
        
        # Determine which metrics to rank on based on strategy
        if strategy == 'value' or 'value' in strategy.lower():
            # For value strategy - lower PE and PB are better
            if 'pe_ratio' in df.columns:
                df['pe_rank'] = df['pe_ratio'].rank()
                
            if 'pb_ratio' in df.columns:
                df['pb_rank'] = df['pb_ratio'].rank()
                
            # Combined value rank if both metrics are available
            if 'pe_rank' in df.columns and 'pb_rank' in df.columns:
                df['value_rank'] = (df['pe_rank'] + df['pb_rank']) / 2
                df = df.sort_values('value_rank')
            elif 'pe_rank' in df.columns:
                df = df.sort_values('pe_rank')
            elif 'pb_rank' in df.columns:
                df = df.sort_values('pb_rank')
                
        elif strategy == 'growth' or 'growth' in strategy.lower():
            # For growth strategy - higher growth rates are better
            growth_metrics = [col for col in df.columns if 'growth' in col.lower()]
            
            for metric in growth_metrics:
                df[f'{metric}_rank'] = df[metric].rank(ascending=False)
                
            if growth_metrics:
                # Create combined rank
                rank_cols = [f'{metric}_rank' for metric in growth_metrics]
                df['growth_rank'] = df[rank_cols].mean(axis=1)
                df = df.sort_values('growth_rank')
                
        elif strategy == 'income' or 'dividend' in strategy.lower():
            # For income strategy - higher yield is better
            if 'dividend_yield' in df.columns:
                df['yield_rank'] = df['dividend_yield'].rank(ascending=False)
                df = df.sort_values('yield_rank')
                
        elif 'reversion' in strategy.lower() or 'low' in strategy.lower():
            # For mean reversion - higher % off high might be better opportunity
            if 'pct_off_high' in df.columns:
                df['reversion_rank'] = df['pct_off_high'].rank(ascending=False)
                df = df.sort_values('reversion_rank')
                
        # If no specific ranking was applied, just return the original
        ranked_results[strategy] = df
        
    return ranked_results

def get_top_stocks_by_strategy(ranked_results, top_n=5):
    """
    Get the top N stocks from each strategy.
    
    Args:
        ranked_results: Dictionary of ranked DataFrames
        top_n: Number of top stocks to return from each strategy
        
    Returns:
        Dictionary with top N stocks for each strategy
    """
    top_stocks = {}
    
    for strategy, results in ranked_results.items():
        if isinstance(results, pd.DataFrame) and not results.empty:
            top_stocks[strategy] = results.head(top_n)
        else:
            top_stocks[strategy] = pd.DataFrame()
            
    return top_stocks

def get_multi_strategy_stocks(ranked_results):
    """
    Find stocks that appear in multiple strategies.
    
    Args:
        ranked_results: Dictionary of ranked DataFrames
        
    Returns:
        DataFrame with stocks that appear in multiple strategies
    """
    all_symbols = set()
    strategy_symbols = {}
    
    # Collect all symbols
    for strategy, results in ranked_results.items():
        if isinstance(results, pd.DataFrame) and not results.empty:
            symbols = results['symbol'].unique().tolist()
            strategy_symbols[strategy] = set(symbols)
            all_symbols.update(symbols)
    
    # Find stocks in multiple strategies
    multi_strategy_stocks = {}
    
    for symbol in all_symbols:
        strategies_present = []
        for strategy, symbols in strategy_symbols.items():
            if symbol in symbols:
                strategies_present.append(strategy)
                
        if len(strategies_present) > 1:
            multi_strategy_stocks[symbol] = strategies_present
    
    # Create DataFrame from results
    if multi_strategy_stocks:
        data = []
        for symbol, strategies in multi_strategy_stocks.items():
            data.append({
                'symbol': symbol,
                'strategies': ', '.join(strategies),
                'strategy_count': len(strategies)
            })
            
        return pd.DataFrame(data).sort_values('strategy_count', ascending=False)
    else:
        return pd.DataFrame()
