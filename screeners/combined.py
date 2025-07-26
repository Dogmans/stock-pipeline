"""
Combined Screener module.
Combines results from multiple screeners based on average ranking.
Supports multiple predefined combinations and custom combinations.
"""

from .common import *

def screen_for_combined(universe_df=None, strategies=None, force_refresh=False, combination_name=None):
    """
    Run multiple screeners and combine their results based on average ranking.
    
    This screener only includes stocks that appear in ALL selected screening strategies.
    If no stocks are found in all screeners, the combined screener will return an empty result.
    
    The combined screener ranks stocks by their average position across all screeners.
    This identifies stocks that perform consistently well across multiple criteria.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe.
        strategies (list): List of screener strategies to combine. 
        force_refresh (bool): Whether to force refresh data from API.
        combination_name (str): Name of predefined combination ('traditional_value', 'high_performance', etc.)
        
    Returns:
        pd.DataFrame: DataFrame containing combined screening results with columns for symbol,
                     average rank, individual ranks, and other metrics.
    """
    
    # Determine which combination to use
    if combination_name:
        combination_config = config.CombinedScreeners.get_combination(combination_name)
        if combination_config:
            strategies = combination_config['strategies']
            combination_description = combination_config['description']
            logger.info(f"Running {combination_config['name']} combined screener: {combination_description}")
        else:
            logger.error(f"Unknown combination name: {combination_name}")
            return pd.DataFrame()
    elif strategies is None:
        # Default to traditional value combination
        combination_config = config.CombinedScreeners.TRADITIONAL_VALUE
        strategies = combination_config['strategies']
        combination_description = combination_config['description']
        logger.info(f"Running {combination_config['name']} combined screener: {combination_description}")
    else:
        logger.info(f"Running custom combined screener with strategies: {strategies}")
        combination_description = f"Custom combination: {', '.join(strategies)}"
    
    # Use either provided universe or get the sp500 by default
    if universe_df is None:
        from universe import get_stock_universe
        universe_df = get_stock_universe()
    
    # Store individual screener results
    screener_results = {}
    
    # Import all screeners
    import importlib
    import sys
    
    # Run each individual screener
    for strategy in strategies:
        try:
            # Construct the function name from the strategy name
            func_name = f"screen_for_{strategy}"
            
            # Import the appropriate module
            module_name = strategy
            if strategy == '52_week_lows':
                module_name = 'fifty_two_week_lows'
                
            try:
                # Try to import the module
                module = importlib.import_module(f'screeners.{module_name}')
                
                # Check if the function exists in the module
                if hasattr(module, func_name):
                    logger.info(f"Running {strategy} screener for combination...")
                    
                    # Get the function from the module
                    screener_func = getattr(module, func_name)
                    
                    # Some strategies may need force_refresh parameter
                    if 'force_refresh' in screener_func.__code__.co_varnames:
                        result = screener_func(universe_df=universe_df, force_refresh=force_refresh)
                    else:
                        result = screener_func(universe_df=universe_df)
                    
                    # Store all results, not just top 10
                    screener_results[strategy] = result
                    
                    # Log the number of stocks that passed the screen
                    if isinstance(result, pd.DataFrame):
                        logger.info(f"Found {len(result)} stocks matching {strategy} criteria")
                else:
                    logger.warning(f"Strategy function '{func_name}' not found in module {module_name}")
            except ImportError:
                logger.warning(f"Strategy module '{module_name}' not found")
                
        except Exception as e:
            logger.error(f"Error running {strategy} screener: {e}")
            screener_results[strategy] = pd.DataFrame()  # Empty DataFrame on error
    
    # Check if we have any results
    if not any(len(df) > 0 for df in screener_results.values()):
        logger.warning("No results from any of the individual screeners")
        return pd.DataFrame()
    
    # Create a dictionary to store ranks for each symbol
    symbol_ranks = {}
    
    # Process each screener's results to assign ranks
    for strategy, result_df in screener_results.items():
        if len(result_df) > 0:
            # Add rank column (1-based ranking)
            result_df['rank'] = range(1, len(result_df) + 1)
            
            # Update the symbol_ranks dictionary
            for _, row in result_df.iterrows():
                symbol = row['symbol']
                rank = row['rank']
                
                if symbol not in symbol_ranks:
                    symbol_ranks[symbol] = {'ranks': [], 'screeners': [], 'details': {}}
                
                symbol_ranks[symbol]['ranks'].append(rank)
                symbol_ranks[symbol]['screeners'].append(strategy)
                
                # Store details from this screener for this symbol
                for col in result_df.columns:
                    if col not in ['rank']:  # Skip the rank column
                        if col not in symbol_ranks[symbol]['details']:
                            symbol_ranks[symbol]['details'][col] = {}
                        symbol_ranks[symbol]['details'][col][strategy] = row[col]
    
    # Debug: Count symbols by the number of screeners they appear in
    screener_counts = {}
    for symbol, data in symbol_ranks.items():
        count = len(data['screeners'])
        if count not in screener_counts:
            screener_counts[count] = 0
        screener_counts[count] += 1
    
    # Log the distribution
    logger.info(f"Symbol distribution across screeners: {screener_counts}")
    
    # Debug: Find symbols that appear in all screeners
    all_screeners_symbols = [symbol for symbol, data in symbol_ranks.items() 
                          if len(data['screeners']) == len(strategies)]
    
    if all_screeners_symbols:
        logger.info(f"Symbols in ALL screeners: {', '.join(all_screeners_symbols)}")
    else:
        logger.info(f"No symbols found in ALL {len(strategies)} screeners")
    
    # Configure threshold for screener inclusion - require ALL screeners
    min_screeners_required = len(strategies)
    # Check if we have any stocks in ALL screeners
    all_screeners_symbols = [symbol for symbol, data in symbol_ranks.items() if len(data['screeners']) == len(strategies)]
    
    if not all_screeners_symbols and len(strategies) > 1:
        logger.warning(f"No stocks found in ALL {len(strategies)} screeners. Combined screener will be empty.")
    
    # Calculate average ranks and create combined results
    combined_results = []
    
    for symbol, data in symbol_ranks.items():
        # Include symbols that appear in at least min_screeners_required
        if len(data['ranks']) >= min_screeners_required:
            avg_rank = sum(data['ranks']) / len(data['ranks'])
            # Apply a slight bonus for appearing in more screeners
            if len(data['ranks']) > min_screeners_required:
                avg_rank = avg_rank - (0.1 * (len(data['ranks']) - min_screeners_required))
            screener_count = len(data['ranks'])
            
            # Get common fields from the first screener where this symbol appeared
            first_screener = data['screeners'][0]
            first_screener_df = screener_results[first_screener]
            
            # Find the row for this symbol
            symbol_row = first_screener_df[first_screener_df['symbol'] == symbol]
            if not symbol_row.empty:
                company_name = symbol_row['company_name'].values[0] if 'company_name' in symbol_row else symbol
                sector = symbol_row['sector'].values[0] if 'sector' in symbol_row else 'Unknown'
                
                # Build rank details string
                rank_details = []
                for i, screener in enumerate(data['screeners']):
                    rank_details.append(f"{screener}: #{data['ranks'][i]}")
                
                # Format metrics for each screener
                metrics = []
                for screener in data['screeners']:
                    if screener == 'pe_ratio' and 'pe_ratio' in data['details'] and screener in data['details']['pe_ratio']:
                        metrics.append(f"P/E: {data['details']['pe_ratio'][screener]:.2f}")
                    elif screener == 'price_to_book' and 'price_to_book' in data['details'] and screener in data['details']['price_to_book']:
                        metrics.append(f"P/B: {data['details']['price_to_book'][screener]:.2f}")
                    elif screener == 'peg_ratio' and 'peg_ratio' in data['details'] and screener in data['details']['peg_ratio']:
                        metrics.append(f"PEG: {data['details']['peg_ratio'][screener]:.2f}")
                    elif screener == '52_week_lows' and 'pct_above_low' in data['details'] and screener in data['details']['pct_above_low']:
                        metrics.append(f"{data['details']['pct_above_low'][screener]:.2f}% above low")
                    elif screener == 'turnaround_candidates' and 'turnaround_score' in data['details'] and screener in data['details']['turnaround_score']:
                        metrics.append(f"Turnaround: {data['details']['turnaround_score'][screener]}")
                
                # Create a reason string
                reason = f"Average rank: {avg_rank:.2f} across {screener_count} screeners ({', '.join(metrics)})"
                
                combined_results.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'avg_rank': avg_rank,
                    'screener_count': screener_count,
                    'rank_details': ', '.join(rank_details),
                    'metrics_summary': ', '.join(metrics),
                    'reason': reason
                })
    
    # Convert to DataFrame
    if not combined_results:
        all_screeners_count = len(strategies)
        if all_screeners_count > 1:
            logger.warning(f"No stocks found in ALL {all_screeners_count} screeners")
            
            # Debug info about stocks in multiple but not all screeners
            all_symbols = set(symbol_ranks.keys())
            logger.info(f"Total unique symbols across all screeners: {len(all_symbols)}")
            
            # Try with less strict requirements
            for required_count in range(all_screeners_count-1, 0, -1):
                matches = [symbol for symbol, data in symbol_ranks.items() 
                          if len(data['screeners']) == required_count]
                if matches:
                    logger.info(f"Found {len(matches)} stocks in exactly {required_count} of {all_screeners_count} screeners")
                    if required_count >= all_screeners_count-1:  # Show symbols if just missing one screener
                        logger.info(f"Symbols in {required_count}/{all_screeners_count} screeners: {', '.join(sorted(matches)[:20])}" + 
                                   ("..." if len(matches) > 20 else ""))
                    break
            
        return pd.DataFrame()
    
    result_df = pd.DataFrame(combined_results)
    
    # Sort by average rank (ascending)
    result_df = result_df.sort_values('avg_rank')
    
    if min_screeners_required == len(strategies):
        logger.info(f"Found {len(result_df)} stocks that appeared in ALL {len(strategies)} screeners")
    else:
        logger.info(f"Found {len(result_df)} stocks that appeared in at least {min_screeners_required} of {len(strategies)} screeners")
    
    return result_df


def screen_for_traditional_value(universe_df=None, force_refresh=False):
    """
    Traditional Value Combined Screener.
    Combines P/E ratio, Price-to-Book, and PEG ratio screeners.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe.
        force_refresh (bool): Whether to force refresh data from API.
        
    Returns:
        pd.DataFrame: Combined screening results for traditional value metrics.
    """
    return screen_for_combined(
        universe_df=universe_df, 
        force_refresh=force_refresh, 
        combination_name='traditional_value'
    )


def screen_for_high_performance(universe_df=None, force_refresh=False):
    """
    High Performance Combined Screener.
    Combines Momentum, Quality, and Free Cash Flow Yield screeners.
    Based on academic research showing strong predictive power.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe.
        force_refresh (bool): Whether to force refresh data from API.
        
    Returns:
        pd.DataFrame: Combined screening results for high-performance metrics.
    """
    return screen_for_combined(
        universe_df=universe_df, 
        force_refresh=force_refresh, 
        combination_name='high_performance'
    )


def screen_for_comprehensive(universe_df=None, force_refresh=False):
    """
    Comprehensive Combined Screener.
    Combines all available screening strategies.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe.
        force_refresh (bool): Whether to force refresh data from API.
        
    Returns:
        pd.DataFrame: Combined screening results for all metrics.
    """
    return screen_for_combined(
        universe_df=universe_df, 
        force_refresh=force_refresh, 
        combination_name='comprehensive'
    )


def screen_for_distressed_value(universe_df=None, force_refresh=False):
    """
    Distressed Value Combined Screener.
    Combines 52-week lows, fallen IPOs, and turnaround candidates.
    
    Args:
        universe_df (pd.DataFrame): DataFrame containing the stock universe.
        force_refresh (bool): Whether to force refresh data from API.
        
    Returns:
        pd.DataFrame: Combined screening results for distressed value opportunities.
    """
    return screen_for_combined(
        universe_df=universe_df, 
        force_refresh=force_refresh, 
        combination_name='distressed_value'
    )
