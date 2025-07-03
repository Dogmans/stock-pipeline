#!/usr/bin/env python3
# filepath: c:\Programs\stock_pipeline\main.py
"""
main.py - Stock Screening Pipeline Main Entry Point

This script runs the complete stock screening pipeline, which:
1. Selects a universe of stocks to analyze
2. Collects price and fundamental data for these stocks
3. Applies various screening strategies based on the Reddit "15 Tools for Stock Picking" post
4. Generates visualizations and reports of the results
5. Alerts about any particularly promising opportunities

Usage:
    python main.py [--universe UNIVERSE] [--strategies STRATEGY1,STRATEGY2,...] [--output OUTPUT_DIR]

Example:
    python main.py --universe sp500 --strategies value,growth,book_to_price --output ./reports
"""

import os
import argparse
from datetime import datetime
import pandas as pd
from tqdm import tqdm

# Import pipeline modules
import config
from utils.logger import setup_logging, get_logger
from utils.filesystem import ensure_directories_exist
from universe import get_stock_universe
from stock_data import get_historical_prices, get_fundamental_data, fetch_52_week_lows
from market_data import get_market_conditions, is_market_in_correction, get_sector_performances
# Updated import to use new screeners package
from screeners.utils import run_all_screeners, get_available_screeners
from reporting import generate_screening_report, generate_metrics_definitions
from cache_config import clear_all_cache, clear_old_cache, get_cache_info

# Import data provider abstraction
import data_providers

def parse_arguments():
    """
    Parse command line arguments for the pipeline.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description='Stock Screening Pipeline')
    
    # Add command line arguments
    parser.add_argument('--universe', type=str, default=config.DEFAULT_UNIVERSE,
                        choices=list(config.UNIVERSES.values()),
                        help='Stock universe to analyze')
    
    # Custom symbol options
    parser.add_argument('--symbols', type=str, default=None,
                        help='Comma-separated list of symbols to analyze (for custom universe)')
    
    parser.add_argument('--symbols-file', type=str, default=None,
                        help='File containing symbols to analyze, one per line or comma-separated')
    
    # Get available screeners
    available_screeners = get_available_screeners()
    parser.add_argument('--strategies', type=str, default='all',
                        help=f'Comma-separated list of screening strategies: {", ".join(available_screeners)}')
    
    parser.add_argument('--output', type=str, default=config.OUTPUT_DIR,
                        help='Directory for output reports and visualizations')
    
    parser.add_argument('--limit', type=int, default=20,
                        help='Limit the number of stocks displayed in results (default: 20 for non-combined screeners)')
    
    # Cache options
    parser.add_argument('--clear-cache', action='store_true',
                        help='Clear the entire cache before running pipeline')
    
    parser.add_argument('--force-refresh', action='store_true',
                        help='Force refresh of all data, bypassing cache')
    
    parser.add_argument('--clear-old-cache', type=float, default=None, metavar='HOURS',
                        help='Clear cache files older than specified hours')
    
    parser.add_argument('--cache-info', action='store_true',
                        help='Display information about the current cache and exit')    # Data provider options
    parser.add_argument('--data-provider', type=str, default=None,
                        choices=['alpha_vantage', 'yfinance', 'financial_modeling_prep', 'finnhub'],
                        help='Data provider to use for financial data')
    
    parser.add_argument('--provider-stats', action='store_true',
                        help='Display statistics about available data providers and exit')
    
    # Note: Chunked processing removed in the Nov 2023 architecture update
    # Each screener now processes stocks individually
    
    # Rate limiting options
    parser.add_argument('--disable-rate-limiting', action='store_true',
                        help='Disable API rate limiting (not recommended)')
    
    parser.add_argument('--custom-rate-limit', type=int, default=None, metavar='CALLS_PER_MINUTE',
                        help='Override the default rate limit for the selected provider')
    
    return parser.parse_args()


def get_universe_filename(base_filename, universe):
    """
    Create a filename that incorporates the universe name.
    
    Args:
        base_filename (str): The original filename without universe (e.g., 'screening_report.md')
        universe (str): The universe name (e.g., 'sp500', 'all', 'russell2000')
        
    Returns:
        str: Filename with universe incorporated (e.g., 'screening_report_sp500.md')
    """
    # Split the filename and extension
    name_parts = base_filename.rsplit('.', 1)
    if len(name_parts) == 2:
        base_name, extension = name_parts
        return f"{base_name}_{universe}.{extension}"
    else:
        # No extension found
        return f"{base_filename}_{universe}"


def main():
    """
    Main function to run the stock screening pipeline.
    """    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging - only here in main.py since this is the entry point
    setup_logging()
    
    # Get a logger for this module
    logger = get_logger(__name__)
    logger.info("Starting stock screening pipeline")
    
    # Create necessary directories
    ensure_directories_exist()
    
    # Handle cache management options
    if args.cache_info:
        cache_info = get_cache_info()
        print("\nCache Information:")
        print(f"Total files: {cache_info['count']}")
        print(f"Total size: {cache_info['total_size_kb']:.2f} KB")
        if cache_info['count'] > 0:
            print(f"Oldest key: {cache_info.get('oldest_key', 'N/A')} ({cache_info.get('oldest_timestamp', 'N/A')})")
            print(f"Newest key: {cache_info.get('newest_key', 'N/A')} ({cache_info.get('newest_timestamp', 'N/A')})")
        print(f"Storage type: {cache_info.get('storage_type', 'N/A')}")
        print(f"Status: {cache_info['status']}")
        return  # Exit after showing cache info
    
    # Clear cache if requested
    if args.clear_cache:
        num_deleted = clear_all_cache()
        logger.info(f"Cleared {num_deleted} cache files")
    
    # Clear old cache files if requested
    if args.clear_old_cache is not None:
        num_deleted = clear_old_cache(args.clear_old_cache)
        logger.info(f"Cleared {num_deleted} cache files older than {args.clear_old_cache} hours")
    
    # Set the output directory
    output_dir = args.output    
    os.makedirs(output_dir, exist_ok=True)
    
    # Select data provider
    if args.data_provider:
        provider_name = args.data_provider
    else:
        provider_name = None  # Use default (Financial Modeling Prep)
    
    data_provider = data_providers.get_provider(provider_name)
    logger.info(f"Using data provider: {data_provider.get_provider_name()}")
    
    # 1. Get the stock universe
    if args.symbols or args.symbols_file:
        logger.info("Using custom stock universe")
        
        if args.symbols_file:
            with open(args.symbols_file, 'r') as f:
                content = f.read().strip()
                if ',' in content:
                    symbols = [s.strip() for s in content.split(',')]
                else:
                    symbols = [s.strip() for s in content.split()]
        else:
            symbols = [s.strip() for s in args.symbols.split(',')]
        
        # Create a DataFrame in the format expected by the pipeline
        universe_df = pd.DataFrame({
            'symbol': symbols,
            'security': [''] * len(symbols),
            'gics_sector': [''] * len(symbols),
            'gics_sub-industry': [''] * len(symbols)
        })
        
        logger.info(f"Selected {len(symbols)} custom symbols for analysis")
    else:
        logger.info(f"Selecting stock universe: {args.universe}")
        universe_df = get_stock_universe(args.universe, force_refresh=args.force_refresh)
    
    # Always process the full universe
    symbols = universe_df['symbol'].tolist()
    universe_size = len(symbols)
    logger.info(f"Selected {universe_size} symbols for analysis")
    
    # Track the original universe size for reporting
    display_limit = args.limit  # Store the display limit for later use
      # 2. Check market conditions
    logger.info("Checking market conditions")
    market_data = get_market_conditions(data_provider=data_provider, force_refresh=args.force_refresh)
    in_correction, market_status = is_market_in_correction(data_provider=data_provider, force_refresh=args.force_refresh)
    sector_performance = get_sector_performances(data_provider=data_provider, force_refresh=args.force_refresh)
    
    logger.info(f"Market status: {market_status}")    # In the new architecture, we directly run the screeners with just the universe data
    # Each screener will fetch its own data directly from the data provider
    
    # Determine which strategies to run
    if args.strategies.lower() == 'all':
        strategies = get_available_screeners()
    else:
        strategies = [s.strip() for s in args.strategies.split(',')]
    
    logger.info(f"Selected strategies: {', '.join(strategies)}")
    
    # Run the screening strategies
    logger.info("Running stock screeners")
    screening_results = run_all_screeners(universe_df, strategies=strategies)
      # 7. Generate screening report
    logger.info("Generating screening report")
      # Sort screening results by relevant metrics for each strategy
    sorted_results = {}
    for strategy_name, results in screening_results.items():
        if isinstance(results, pd.DataFrame) and not results.empty:
            # Sort based on strategy-specific metrics
            if strategy_name == 'value' and 'pe_ratio' in results.columns:
                # For value, lower P/E is better
                sorted_results[strategy_name] = results.sort_values('pe_ratio')
            elif strategy_name == 'peg_ratio' and 'peg_ratio' in results.columns:
                # For PEG, lower ratio is better
                sorted_results[strategy_name] = results.sort_values('peg_ratio')
            elif strategy_name == 'combined' and 'avg_rank' in results.columns:
                # For combined screener, lower average rank is better
                sorted_results[strategy_name] = results.sort_values('avg_rank')
            elif strategy_name == 'growth' and 'growth_rate' in results.columns:
                # For growth, higher growth rate is better
                sorted_results[strategy_name] = results.sort_values('growth_rate', ascending=False)
            elif strategy_name == 'income' and 'dividend_yield' in results.columns:
                # For income, higher yield is better
                sorted_results[strategy_name] = results.sort_values('dividend_yield', ascending=False)
            elif strategy_name == 'turnaround' and 'turnaround_score' in results.columns:
                # For turnaround, higher score is better
                sorted_results[strategy_name] = results.sort_values('turnaround_score', ascending=False)
            elif 'pct_off_high' in results.columns:
                # For mean reversion, higher percentage off high might be better
                sorted_results[strategy_name] = results.sort_values('pct_off_high', ascending=False)
            else:
                # Default case, just keep original order
                sorted_results[strategy_name] = results
        else:
            sorted_results[strategy_name] = results
    
    # Generate comprehensive markdown report
    report_filename = get_universe_filename('screening_report.md', args.universe)
    report_path = os.path.join(output_dir, report_filename)
    generate_screening_report(sorted_results, report_path)
      
    # Also generate a summary file
    summary_filename = get_universe_filename('summary.txt', args.universe)
    summary_path = os.path.join(output_dir, summary_filename)
    with open(summary_path, 'w') as f:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"Stock Screening Pipeline - Summary Report\n")
        f.write(f"Generated: {current_time}\n\n")
        
        # Add universe and market info
        universe_size = len(universe_df) if universe_df is not None else 0
        # Include display limit info if specified
        if display_limit:
            f.write(f"Universe: {args.universe} ({universe_size} stocks, displaying top {display_limit} for each strategy)\n")
        else:
            f.write(f"Universe: {args.universe} ({universe_size} stocks)\n")
          # Add market conditions if available
        try:
            import market_data
            market_conditions = market_data.get_market_conditions()
            vix = market_conditions.get('vix', 'N/A')
            f.write(f"Market Status: {market_conditions.get('status', 'Unknown')} (VIX: {vix})\n")
        except:
            pass
        
        f.write("\nTop Candidates by Strategy:\n\n")            # Write each strategy's results
        for strategy_name, results in sorted_results.items():
            if not isinstance(results, pd.DataFrame) or results.empty:
                continue
                
            readable_name = strategy_name.lower()
            f.write(f"{readable_name}:\n")
            
            # For individual screeners (not combined), use meets_threshold if available, otherwise top N
            if strategy_name != 'combined' and 'meets_threshold' in results.columns:
                # Get only stocks meeting the threshold
                filtered_results = results[results['meets_threshold'] == True]
                
                # If fewer than N stocks meet the threshold or it's a combined screener, show top N instead
                if len(filtered_results) < 5:
                    # For display, take top 10 from full results
                    display_results = results.head(10)
                else:
                    # Otherwise show all that meet threshold (up to 10)
                    display_results = filtered_results.head(10)
            else:
                # For combined screener or screeners without meets_threshold, just show top results
                # Apply a lower limit for the combined screener (10) than other screeners (use the display_limit, default 20)
                # Special case: If limit is 0, show all results
                if display_limit == 0:
                    display_count = len(results)
                    display_results = results
                elif strategy_name == 'combined':
                    display_count = min(display_limit if display_limit else 10, len(results))
                    display_results = results.head(display_count)
                else:
                    display_count = min(display_limit, len(results))
                    display_results = results.head(display_count)
                
                for idx in range(display_count):
                    if idx < len(display_results):
                        row = display_results.iloc[idx]
                        symbol = row['symbol']
                  # Format based on the strategy type
                if strategy_name == 'pe_ratio' and 'pe_ratio' in row:
                    f.write(f"  {symbol}:  Low P/E ratio (P/E = {row['pe_ratio']:.2f})\n")
                elif strategy_name == 'price_to_book' and 'price_to_book' in row:
                    f.write(f"  {symbol}:  Low price to book ratio (P/B = {row['price_to_book']:.2f})\n")
                elif strategy_name == 'peg_ratio' and 'peg_ratio' in row:
                    f.write(f"  {symbol}:  Low PEG ratio ({row['peg_ratio']:.2f}) - P/E: {row['pe_ratio']:.2f}, Growth: {row['growth_rate']:.1f}%\n")
                elif '52_week_low' in strategy_name and 'pct_above_low' in row:
                    f.write(f"  {symbol}:  Near 52-week low ({row['pct_above_low']:.2f}% above low)\n")
                    
                elif 'fallen_ipo' in strategy_name and 'pct_off_high' in row:
                    f.write(f"  {symbol}:  Fallen IPO ({row['pct_off_high']:.2f}% off high)\n")
                elif strategy_name == 'turnaround_candidates' and 'reason' in row:
                    # Enhanced turnaround display with reason
                    f.write(f"  {symbol}:  {row['primary_factor']} ({row['reason']})\n")
                elif strategy_name == 'combined' and 'avg_rank' in row:
                    # Special format for combined screener results
                    f.write(f"  {symbol}:  Avg rank: {row['avg_rank']:.2f} across {row['screener_count']} screeners ({row['metrics_summary']})\n")
                else:
                    # Generic format for other strategies
                    f.write(f"  {symbol}\n")
            
            f.write("\n")
        
        f.write("\nRun 'python main.py --help' for more options.")
    
    logger.info(f"Report generated: {report_path}")
    
    # 8. Output summary
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summary_filename = get_universe_filename('summary.txt', args.universe)
    summary_path = os.path.join(output_dir, summary_filename)
    
    with open(summary_path, 'w') as f:
        f.write(f"Stock Screening Pipeline - Summary Report\n")
        f.write(f"Generated: {timestamp}\n\n")
        f.write(f"Universe: {args.universe} ({len(symbols)} stocks)\n")
        f.write(f"Market Status: {market_status}\n\n")
        
        f.write("Top Candidates by Strategy:\n")
        for strategy_name, results in screening_results.items():
            if isinstance(results, pd.DataFrame) and not results.empty:
                f.write(f"\n{strategy_name}:\n")
                
                # For individual screeners (not combined), filter by meets_threshold if available
                if strategy_name != 'combined' and 'meets_threshold' in results.columns:
                    # Get only stocks meeting the threshold
                    filtered_results = results[results['meets_threshold'] == True]
                    
                    # If fewer than N stocks meet the threshold, show top N instead
                    if len(filtered_results) < 5:
                        # For display, apply the display limit to full results (default 20)
                        display_results = results.head(display_limit)
                    else:
                        # Otherwise show all that meet threshold (up to the display limit)
                        display_results = filtered_results.head(display_limit)
                else:
                    # Special case: If limit is 0, show all results
                    if display_limit == 0:
                        display_results = results
                    else:
                        # For combined screener, use a smaller default limit
                        if strategy_name == 'combined':
                            max_display = min(display_limit if display_limit else 10, len(results))
                        else:
                            # For non-combined screeners without meets_threshold, use the normal display limit
                            max_display = display_limit
                        display_results = results.head(max_display)
                
                # Write out the results
                for i, row in display_results.iterrows():
                    f.write(f"  {row['symbol']}: {row.get('score', '')} {row.get('reason', '')}\n")
    
    logger.info(f"Pipeline complete. Results saved to {output_dir} with {args.universe} universe")
    logger.info(f"Report available at: {report_path}")
    logger.info(f"Summary report: {summary_path}")


if __name__ == "__main__":
    main()
