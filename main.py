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
    
    # Get available screeners
    available_screeners = get_available_screeners()
    parser.add_argument('--strategies', type=str, default='all',
                        help=f'Comma-separated list of screening strategies: {", ".join(available_screeners)}')
    
    parser.add_argument('--output', type=str, default=config.OUTPUT_DIR,
                        help='Directory for output reports and visualizations')
    
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit the number of stocks processed (for testing)')
    
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
    
    # Set the output directory
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Get the stock universe
    logger.info(f"Selecting stock universe: {args.universe}")
    universe_df = get_stock_universe(args.universe)
    
    # If a limit is specified, take only that many stocks
    if args.limit:
        universe_df = universe_df.head(args.limit)
    
    symbols = universe_df['symbol'].tolist()
    logger.info(f"Selected {len(symbols)} symbols for analysis")
    
    # 2. Check market conditions
    logger.info("Checking market conditions")
    market_data = get_market_conditions()
    in_correction, market_status = is_market_in_correction()
    sector_performance = get_sector_performances()
    
    logger.info(f"Market status: {market_status}")
    
    # 3. Get historical price data
    logger.info("Fetching historical price data")
    price_data = get_historical_prices(symbols)
    logger.info(f"Retrieved price data for {len(price_data)} symbols")
    
    # 4. Get fundamental data
    logger.info("Fetching fundamental data")
    fundamental_data = get_fundamental_data(symbols)
    logger.info(f"Retrieved fundamental data for {len(fundamental_data)} symbols")
    
    # 5. Process data
    logger.info("Processing stock data")
    processed_data = process_stock_data(price_data, fundamental_data)
    financial_ratios = calculate_financial_ratios(fundamental_data)
    
    # 6. Run screeners
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
