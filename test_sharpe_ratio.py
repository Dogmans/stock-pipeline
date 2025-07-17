#!/usr/bin/env python3
"""
Test script to verify the Sharpe ratio screener works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screeners.sharpe_ratio import screen_for_sharpe_ratio

def test_sharpe_ratio_screener():
    """Test the Sharpe ratio screener with a small universe."""
    
    # Create a test universe with known stocks
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    test_universe = pd.DataFrame({
        'symbol': test_symbols,
        'company_name': [f'Test Company {s}' for s in test_symbols]
    })
    
    print("Testing Sharpe ratio screener...")
    print(f"Test universe: {test_symbols}")
    
    try:
        # Run the screener with a low threshold to get some results
        results = screen_for_sharpe_ratio(test_universe, min_sharpe_ratio=0.5)
        
        print(f"\nResults returned: {len(results)} stocks")
        
        if len(results) > 0:
            print("\nTop 10 results by Sharpe ratio:")
            for i, (_, row) in enumerate(results.head(10).iterrows()):
                print(f"  {i+1}. {row['symbol']}: Sharpe = {row['sharpe_ratio']:.2f}, "
                      f"Annual Return = {row['annual_return']:.1%}, "
                      f"Volatility = {row['annual_volatility']:.1%}, "
                      f"Meets threshold: {row['meets_threshold']}")
        else:
            print("No stocks passed the Sharpe ratio screening")
            
    except Exception as e:
        print(f"Error running screener: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sharpe_ratio_screener()
