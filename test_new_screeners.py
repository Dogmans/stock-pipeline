"""
Test script for the new high-performance screeners.
Tests momentum, quality, and free cash flow yield screeners.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screeners.momentum import screen_for_momentum
from screeners.quality import screen_for_quality
from screeners.free_cash_flow_yield import screen_for_free_cash_flow_yield

def test_new_screeners():
    """Test the new screeners with a small sample."""
    print("Testing new high-performance screeners...")
    
    # Create a test universe with some well-known stocks
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B', 'JNJ', 'V']
    test_universe = pd.DataFrame({'symbol': test_symbols})
    
    print(f"Test universe: {len(test_universe)} stocks")
    print()
    
    # Test Momentum Screener
    print("1. Testing Momentum Screener...")
    try:
        momentum_results = screen_for_momentum(test_universe, min_momentum_score=5.0)  # Lower threshold for testing
        print(f"   Found {len(momentum_results)} stocks with momentum data")
        if not momentum_results.empty:
            print("   Top 3 momentum stocks:")
            for _, row in momentum_results.head(3).iterrows():
                print(f"     {row['symbol']}: {row['reason']}")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test Quality Screener
    print("2. Testing Quality Screener...")
    try:
        quality_results = screen_for_quality(test_universe, min_quality_score=3.0)  # Lower threshold for testing
        print(f"   Found {len(quality_results)} stocks with quality data")
        if not quality_results.empty:
            print("   Top 3 quality stocks:")
            for _, row in quality_results.head(3).iterrows():
                print(f"     {row['symbol']}: {row['reason']}")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test Free Cash Flow Yield Screener
    print("3. Testing Free Cash Flow Yield Screener...")
    try:
        fcf_results = screen_for_free_cash_flow_yield(test_universe, min_fcf_yield=3.0)  # Lower threshold for testing
        print(f"   Found {len(fcf_results)} stocks with FCF data")
        if not fcf_results.empty:
            print("   Top 3 FCF yield stocks:")
            for _, row in fcf_results.head(3).iterrows():
                print(f"     {row['symbol']}: {row['reason']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_new_screeners()
