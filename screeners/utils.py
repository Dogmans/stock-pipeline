"""
Utility functions for the stock screeners package.
"""

import importlib
import inspect
import logging
import sys
import pandas as pd

# Get logger for this module
from utils.logger import get_logger
logger = get_logger(__name__)

def get_available_screeners():
    """
    Get a list of all available screener strategy names.
    
    Returns:
        list: List of strategy names (strings)
    """
    # Import the screeners package to access all modules
    import screeners
    
    # List all the screening functions in the package
    screener_functions = []
    
    # Get all modules in the screeners package
    modules = [
        'pe_ratio', 'price_to_book', 'fifty_two_week_lows', 
        'fallen_ipos', 'turnaround_candidates', 'peg_ratio', 
        'sector_corrections', 'combined', 'sharpe_ratio',
        'momentum', 'quality', 'free_cash_flow_yield'
    ]
    
    # Special handling for combined screeners
    combined_screeners = [
        'combined', 'traditional_value', 'high_performance', 
        'comprehensive', 'distressed_value'
    ]
    
    for module_name in modules:
        try:
            module = importlib.import_module(f'screeners.{module_name}')
            for name, obj in inspect.getmembers(module):
                if (name.startswith('screen_for_') and 
                    inspect.isfunction(obj)):
                    screener_name = name.replace('screen_for_', '')
                    if screener_name not in screener_functions:
                        screener_functions.append(screener_name)
        except ImportError as e:
            logger.error(f"Error importing module {module_name}: {e}")
    
    # Add combined screeners that aren't automatically discovered
    for combined_name in combined_screeners:
        if combined_name not in screener_functions:
            screener_functions.append(combined_name)
        
    return sorted(screener_functions)


def run_all_screeners(universe_df, strategies=None, auto_run_combined=True):
    """
    Run all the specified screeners on the given stock universe.
    Each screener function will fetch its own data directly from the data provider.
    
    Args:
        universe_df (DataFrame): The stock universe being analyzed
        strategies (list, optional): List of strategy names to run, or None for all
        auto_run_combined (bool): If True, automatically run the combined screener if more 
                                than one regular screener is specified
    
    Returns:
        dict: Dictionary mapping strategy names to DataFrames with screening results
    """
    # Import here to avoid circular imports
    import screeners
    
    # If no strategies specified, run all of them
    if strategies is None:
        strategies = get_available_screeners()
    
    # Filter out 'combined' from the input strategies to avoid duplication
    regular_strategies = [s for s in strategies if s != 'combined']
    
    results = {}
    
    for strategy in regular_strategies:
        try:
            # Construct the function name from the strategy name
            func_name = f"screen_for_{strategy}"
            
            # Get the function from the screeners package
            screener_func = getattr(screeners, func_name, None)
            
            # Check if the function exists
            if screener_func and callable(screener_func):
                logger.info(f"Running {strategy} screener...")
                
                # Call the screener function with only the universe data
                # Each screener will fetch its own data from the provider
                result = screener_func(universe_df=universe_df)
                
                # Store the result
                results[strategy] = result
                
                # Log the number of stocks that passed the screen
                if isinstance(result, pd.DataFrame):
                    logger.info(f"Found {len(result)} stocks matching {strategy} criteria")
            else:
                logger.warning(f"Strategy '{strategy}' not found or not callable")
                
        except Exception as e:
            logger.error(f"Error running {strategy} screener: {e}")
            results[strategy] = pd.DataFrame()  # Empty DataFrame on error
    
    # Automatically run the combined screener if more than one strategy is running
    # and if it wasn't explicitly specified (to avoid running it twice)
    if auto_run_combined and len(regular_strategies) > 1 and 'combined' not in strategies:
        logger.info("Automatically running combined screener...")
        
        try:
            # Run combined screener with the results from individual screeners
            combined_results = screeners.screen_for_combined(universe_df=universe_df, strategies=regular_strategies)
            results['combined'] = combined_results
        except Exception as e:
            logger.error(f"Error running combined screener: {e}")
            results['combined'] = pd.DataFrame()
    
    # If 'combined' was explicitly requested, run it with all other strategies
    elif 'combined' in strategies:
        logger.info("Running explicitly requested combined screener...")
        
        try:
            # Run combined screener with the results from individual screeners
            combined_results = screeners.screen_for_combined(universe_df=universe_df, strategies=regular_strategies)
            results['combined'] = combined_results
        except Exception as e:
            logger.error(f"Error running combined screener: {e}")
            results['combined'] = pd.DataFrame()
    
    return results
