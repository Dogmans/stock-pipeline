#!/usr/bin/env python3
# filepath: c:\Programs\stock_pipeline\create_symbol_chunks.py
"""
Script to split stock universe into manageable chunks.

This script divides a stock universe into smaller chunks that can be processed
within the API limits of free data providers.

Usage:
    python create_symbol_chunks.py --universe sp500 --chunk-size 200
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from universe import get_stock_universe
from utils import setup_logging

logger = setup_logging()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Split stock universe into chunks')
    
    parser.add_argument('--universe', type=str, default='sp500',
                        choices=['sp500', 'russell2000', 'nasdaq100', 'all'],
                        help='Stock universe to split')
    
    parser.add_argument('--chunk-size', type=int, default=200,
                        help='Size of each chunk (symbols per file)')
    
    parser.add_argument('--output-dir', type=str, default='.',
                        help='Directory to save chunk files')
    
    parser.add_argument('--force-refresh', action='store_true',
                        help='Force refresh of universe data')
    
    return parser.parse_args()

def create_chunks(symbols, chunk_size, output_dir, universe_name):
    """Split symbols into chunks and save to files."""
    # Convert symbols to array if it's a DataFrame
    if isinstance(symbols, pd.DataFrame):
        symbols = symbols['symbol'].tolist()
    
    # Split into chunks
    chunks = np.array_split(symbols, max(1, len(symbols) // chunk_size + (1 if len(symbols) % chunk_size else 0)))
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save each chunk to a file
    for i, chunk in enumerate(chunks):
        chunk_list = chunk.tolist() if isinstance(chunk, np.ndarray) else list(chunk)
        filename = os.path.join(output_dir, f'{universe_name}_chunk{i+1}.txt')
        
        with open(filename, 'w') as f:
            f.write(','.join(chunk_list))
        
        logger.info(f'Created chunk {i+1} with {len(chunk_list)} symbols: {filename}')
    
    return len(chunks)

def main():
    """Main function."""
    args = parse_arguments()
    
    logger.info(f'Retrieving {args.universe} universe...')
    universe_df = get_stock_universe(args.universe, force_refresh=args.force_refresh)
    
    if universe_df.empty:
        logger.error(f'Failed to retrieve {args.universe} universe')
        sys.exit(1)
    
    logger.info(f'Retrieved {len(universe_df)} symbols from {args.universe} universe')
    
    # Create chunks
    num_chunks = create_chunks(
        universe_df, 
        args.chunk_size, 
        args.output_dir,
        args.universe
    )
    
    logger.info(f'Created {num_chunks} chunks of {args.chunk_size} symbols each')
    logger.info(f'Run pipeline for each chunk with: python main.py --universe custom --symbols-file "[chunk_file]"')

if __name__ == '__main__':
    main()
