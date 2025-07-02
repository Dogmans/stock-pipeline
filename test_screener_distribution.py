"""
A diagnostic script to analyze why stocks don't appear in all screeners
"""

import pandas as pd
# Updated imports to use new screeners package structure
from screeners.pe_ratio import screen_for_pe_ratio
from screeners.price_to_book import screen_for_price_to_book
from screeners.peg_ratio import screen_for_peg_ratio
from universe import get_stock_universe
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get universe data
universe_df = get_stock_universe()
logger.info(f"Universe contains {len(universe_df)} stocks")

# Run each screener
pe_results = screen_for_pe_ratio(universe_df)
pb_results = screen_for_price_to_book(universe_df)
peg_results = screen_for_peg_ratio(universe_df)

# Get unique symbols from each screener
pe_symbols = set(pe_results['symbol'])
pb_symbols = set(pb_results['symbol'])
peg_symbols = set(peg_results['symbol'])

logger.info(f"PE ratio screener: {len(pe_symbols)} stocks")
logger.info(f"Price-to-book screener: {len(pb_symbols)} stocks")
logger.info(f"PEG ratio screener: {len(peg_symbols)} stocks")

# Find stocks that appear in some but not all screeners
in_pe_only = pe_symbols - (pb_symbols | peg_symbols)
in_pb_only = pb_symbols - (pe_symbols | peg_symbols)
in_peg_only = peg_symbols - (pe_symbols | pb_symbols)

in_pe_and_pb = pe_symbols & pb_symbols - peg_symbols
in_pe_and_peg = pe_symbols & peg_symbols - pb_symbols
in_pb_and_peg = pb_symbols & peg_symbols - pe_symbols

in_all = pe_symbols & pb_symbols & peg_symbols

# Print results
logger.info(f"Stocks in PE only: {len(in_pe_only)}")
if in_pe_only:
    logger.info(f"Examples: {list(in_pe_only)[:5]}")

logger.info(f"Stocks in P/B only: {len(in_pb_only)}")
if in_pb_only:
    logger.info(f"Examples: {list(in_pb_only)[:5]}")

logger.info(f"Stocks in PEG only: {len(in_peg_only)}")
if in_peg_only:
    logger.info(f"Examples: {list(in_peg_only)[:5]}")

logger.info(f"Stocks in PE & P/B but not PEG: {len(in_pe_and_pb)}")
if in_pe_and_pb:
    logger.info(f"Examples: {list(in_pe_and_pb)[:5]}")

logger.info(f"Stocks in PE & PEG but not P/B: {len(in_pe_and_peg)}")
if in_pe_and_peg:
    logger.info(f"Examples: {list(in_pe_and_peg)[:5]}")

logger.info(f"Stocks in P/B & PEG but not PE: {len(in_pb_and_peg)}")
if in_pb_and_peg:
    logger.info(f"Examples: {list(in_pb_and_peg)[:5]}")

logger.info(f"Stocks in ALL screeners: {len(in_all)}")
