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
import sys
import logging
import argparse
from datetime import datetime
import pandas as pd

# Import pipeline modules
import config
from utils import setup_logging, ensure_directories_exist
from universe import get_stock_universe
from stock_data import get_historical_prices, get_fundamental_data, fetch_52_week_lows
from market_data import get_market_conditions, is_market_in_correction, get_sector_performances
from data_processing import process_stock_data, calculate_financial_ratios
from screeners import run_all_screeners, get_available_screeners
from visualization import create_dashboard, create_stock_charts, create_market_overview
from cache_manager import clear_cache, get_cache_info

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
    
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit the number of stocks processed (for testing)')
    
    # Cache options
    parser.add_argument('--clear-cache', action='store_true',
                        help='Clear the entire cache before running pipeline')
    
    parser.add_argument('--force-refresh', action='store_true',
                        help='Force refresh of all data, bypassing cache')
    
    parser.add_argument('--clear-old-cache', type=float, default=None, metavar='HOURS',
                        help='Clear cache files older than specified hours')
    
    parser.add_argument('--cache-info', action='store_true',
                        help='Display information about the current cache and exit')
    
    # Data provider options
    parser.add_argument('--data-provider', type=str, default=None,
                        choices=['alpha_vantage', 'yfinance', 'financial_modeling_prep', 'finnhub', 'multi'],
                        help='Data provider to use for financial data')
    
    parser.add_argument('--provider-stats', action='store_true',
                        help='Display statistics about available data providers and exit')
    
    parser.add_argument('--chunk-size', type=int, default=None,
                        help='Process symbols in chunks of this size to stay within API limits')
    
    parser.add_argument('--multi-source', action='store_true',
                        help='Use multiple data sources with automatic failover')
    
    return parser.parse_args()


def main():
    """
    Main function to run the stock screening pipeline.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging()
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
            print(f"Oldest file: {cache_info['oldest_file']} ({cache_info['oldest_timestamp']})")
            print(f"Newest file: {cache_info['newest_file']} ({cache_info['newest_timestamp']})")
        print(f"Cache directory: {cache_info['cache_dir']}")
        print(f"Status: {cache_info['status']}")
        return  # Exit after showing cache info
    
    # Clear cache if requested
    if args.clear_cache:
        num_deleted = clear_cache()
        logger.info(f"Cleared {num_deleted} cache files")
    
    # Clear old cache files if requested
    if args.clear_old_cache is not None:
        num_deleted = clear_cache(older_than_hours=args.clear_old_cache)
        logger.info(f"Cleared {num_deleted} cache files older than {args.clear_old_cache} hours")
    
    # Set the output directory
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # Select data provider
    if args.multi_source:
        provider_name = 'multi'
    elif args.data_provider:
        provider_name = args.data_provider
    else:
        provider_name = None  # Use default
    
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
    
    # If a limit is specified, take only that many stocks
    if args.limit:
        universe_df = universe_df.head(args.limit)
    
    # If chunking is specified, warn about it
    if args.chunk_size and len(universe_df) > args.chunk_size:
        logger.warning(
            f"Processing {len(universe_df)} symbols at once may exceed API limits. "
            f"Consider using create_symbol_chunks.py to split into chunks of {args.chunk_size} symbols."
        )
    
    symbols = universe_df['symbol'].tolist()
    logger.info(f"Selected {len(symbols)} symbols for analysis")
      # 2. Check market conditions
    logger.info("Checking market conditions")
    market_data = get_market_conditions(data_provider=data_provider, force_refresh=args.force_refresh)
    in_correction, market_status = is_market_in_correction(data_provider=data_provider, force_refresh=args.force_refresh)
    sector_performance = get_sector_performances(data_provider=data_provider, force_refresh=args.force_refresh)
    
    logger.info(f"Market status: {market_status}")    # 3. Get historical price data using the selected provider
    logger.info("Fetching historical price data")
    price_data = {}
    
    if args.chunk_size and len(symbols) > args.chunk_size:
        # Process prices in chunks to respect API limits
        chunks = [symbols[i:i+args.chunk_size] for i in range(0, len(symbols), args.chunk_size)]
        logger.info(f"Processing price data in {len(chunks)} chunks of {args.chunk_size} symbols each")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing price chunk {i+1}/{len(chunks)} with {len(chunk)} symbols")
            chunk_data = data_provider.get_historical_prices(
                chunk, 
                period="1y", 
                interval="1d",
                force_refresh=args.force_refresh
            )
            price_data.update(chunk_data)
    else:
        # Process all symbols at once
        price_data = data_provider.get_historical_prices(
            symbols, 
            period="1y", 
            interval="1d", 
            force_refresh=args.force_refresh
        )
            
    logger.info(f"Retrieved price data for {len(price_data)} symbols")
    
    # 4. Get fundamental data using the selected provider
    logger.info("Fetching fundamental data")
    fundamental_data = {}
    
    if args.chunk_size and len(symbols) > args.chunk_size:
        # Process in chunks to respect API limits
        chunks = [symbols[i:i+args.chunk_size] for i in range(0, len(symbols), args.chunk_size)]
        logger.info(f"Processing fundamental data in {len(chunks)} chunks of {args.chunk_size} symbols each")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} with {len(chunk)} symbols")
            chunk_data = data_provider.get_batch_fundamental_data(
                chunk, 
                force_refresh=args.force_refresh,
                max_workers=5,
                rate_limit=data_provider.RATE_LIMIT if hasattr(data_provider, 'RATE_LIMIT') and data_provider.RATE_LIMIT else None
            )
            fundamental_data.update(chunk_data)
    else:
        # Process all symbols at once
        for symbol in symbols:
            try:
                data = data_provider.get_fundamental_data(symbol, force_refresh=args.force_refresh)
                if data:
                    fundamental_data[symbol] = data
            except Exception as e:
                logger.error(f"Error getting fundamental data for {symbol}: {e}")
    
    logger.info(f"Retrieved fundamental data for {len(fundamental_data)} symbols")
    
    # 3. Process and clean the data
    logger.info("Processing and cleaning data")
    processed_data = process_stock_data(price_data, fundamental_data)
    
    # 4. Calculate financial ratios
    logger.info("Calculating financial ratios")
    financial_ratios = calculate_financial_ratios(processed_data)
      # We already have market_data and sector_performance from earlier, 
    # no need to fetch them again - just reuse the existing values
    
    # 6. Run the screening strategies
    logger.info("Running stock screeners")
    
    # Determine which strategies to run
    if args.strategies.lower() == 'all':
        strategies = get_available_screeners()
    else:
        strategies = [s.strip() for s in args.strategies.split(',')]
    
    logger.info(f"Selected strategies: {', '.join(strategies)}")
    
    # Run the screening strategies
    screening_results = run_all_screeners(
        processed_data, 
        financial_ratios,
        market_data,
        universe_df,
        strategies=strategies
    )
    
    # 7. Create visualizations
    logger.info("Creating visualizations and reports")
    
    # Create dashboard with all results
    dashboard_path = os.path.join(output_dir, 'dashboard.html')
    create_dashboard(screening_results, market_data, sector_performance, dashboard_path)
    
    # Create stock charts for top candidates
    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    top_candidates = []
    for strategy_name, results in screening_results.items():
        if isinstance(results, pd.DataFrame) and not results.empty:
            # Tag each stock with the strategy that identified it
            results['strategy'] = strategy_name
            top_candidates.append(results.head(5))
    
    if top_candidates:
        top_candidates_df = pd.concat(top_candidates)
        create_stock_charts(top_candidates_df['symbol'].unique().tolist(), price_data, charts_dir)
    
    # Create market overview
    market_overview_path = os.path.join(output_dir, 'market_overview.html')
    create_market_overview(market_data, sector_performance, market_overview_path)
    
    # 8. Output summary
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summary_path = os.path.join(output_dir, 'summary.txt')
    
    with open(summary_path, 'w') as f:
        f.write(f"Stock Screening Pipeline - Summary Report\n")
        f.write(f"Generated: {timestamp}\n\n")
        f.write(f"Universe: {args.universe} ({len(symbols)} stocks)\n")
        f.write(f"Market Status: {market_status}\n\n")
        
        f.write("Top Candidates by Strategy:\n")
        for strategy_name, results in screening_results.items():
            if isinstance(results, pd.DataFrame) and not results.empty:
                f.write(f"\n{strategy_name}:\n")
                for i, row in results.head(10).iterrows():
                    f.write(f"  {row['symbol']}: {row.get('score', '')} {row.get('reason', '')}\n")
    
    logger.info(f"Pipeline complete. Results saved to {output_dir}")
    logger.info(f"Dashboard available at: {dashboard_path}")
    logger.info(f"Summary report: {summary_path}")


if __name__ == "__main__":
    main()
