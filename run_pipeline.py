#!/usr/bin/env python3
# filepath: c:\Programs\stock_pipeline\run_pipeline.py
"""
Wrapper script to run the stock screening pipeline with commonly used options.
This script simplifies running the pipeline for common use cases.
"""

import argparse
import sys
import time
import datetime
import subprocess

def main():
    """Run the stock screening pipeline with common options."""
    parser = argparse.ArgumentParser(description="Run stock screening pipeline with common options")
    
    # Add command line arguments
    parser.add_argument('--quick', action='store_true',
                      help='Run a quick scan with limited universe (SP500) and basic strategies')
    
    parser.add_argument('--full', action='store_true',
                      help='Run a comprehensive scan with all universes and strategies')
    
    parser.add_argument('--value', action='store_true',
                      help='Run value-focused strategies (price_to_book, pe_ratio)')
    
    parser.add_argument('--output', type=str, default='./output',
                      help='Output directory for reports')
    
    args = parser.parse_args()
    
    # Build the command
    cmd = ['python', 'main.py']
    
    if args.quick:
        print("Running quick scan...")
        cmd.extend(['--universe', 'sp500', 
                    '--strategies', 'price_to_book,pe_ratio,52_week_lows',
                    '--limit', '100'])
    elif args.full:
        print("Running full comprehensive scan (this may take a while)...")
        cmd.extend(['--universe', 'all'])
    elif args.value:
        print("Running value-focused scan...")
        cmd.extend(['--universe', 'sp500', 
                    '--strategies', 'price_to_book,pe_ratio,cash_rich_biotech'])
    
    cmd.extend(['--output', args.output])
    
    # Print the command we're running
    print(f"Executing: {' '.join(cmd)}")
    print("-" * 80)
    
    # Start time
    start_time = time.time()
    
    # Run the command
    result = subprocess.run(cmd)
    
    # End time
    end_time = time.time()
    elapsed = end_time - start_time
    
    print("-" * 80)
    print(f"Pipeline completed with exit code {result.returncode}")
    print(f"Total execution time: {datetime.timedelta(seconds=int(elapsed))}")
    
    if result.returncode == 0:
        print(f"Results saved to: {args.output}")
    else:
        print("Pipeline execution failed. Check the logs for details.")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
