#!/usr/bin/env python3
"""
Test script to verify the price-to-book ratio fix.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screeners.price_to_book import screen_for_price_to_book

def test_price_to_book_fix():
    """Test that the price-to-book screener now filters out zero values."""
    
    # Create a small test universe with known problematic symbols
    test_symbols = ['BATRA', 'SMID', 'SENEA', 'MLAB', 'KG', 'AAPL', 'MSFT']
    test_universe = pd.DataFrame({
        'symbol': test_symbols,
        'company_name': [f'Test Company {s}' for s in test_symbols]
    })
    
    print("Testing price-to-book screener with known problematic symbols...")
    print(f"Test universe: {test_symbols}")
    
    try:
        # Run the screener
        results = screen_for_price_to_book(test_universe, max_pb_ratio=10.0)
        
        print(f"\nResults returned: {len(results)} stocks")
        
        if len(results) > 0:
            print("\nResults:")
            for _, row in results.iterrows():
                print(f"  {row['symbol']}: P/B = {row['price_to_book']:.2f}, Meets threshold: {row['meets_threshold']}")
        else:
            print("No stocks passed the price-to-book screening (this is expected if all had P/B = 0)")
            
        # Check if any of the known zero-P/B stocks made it through
        zero_pb_symbols = ['BATRA', 'SMID', 'SENEA', 'MLAB', 'KG']
        found_zero_pb = []
        
        for symbol in zero_pb_symbols:
            if symbol in results['symbol'].values:
                pb_value = results[results['symbol'] == symbol]['price_to_book'].iloc[0]
                found_zero_pb.append((symbol, pb_value))
        
        if found_zero_pb:
            print(f"\nWARNING: Found stocks with suspicious P/B values:")
            for symbol, pb in found_zero_pb:
                print(f"  {symbol}: P/B = {pb}")
        else:
            print(f"\n✓ SUCCESS: All stocks with zero P/B ratios were correctly filtered out")
            
    except Exception as e:
        print(f"Error running screener: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_price_to_book_fix()
