#!/usr/bin/env python3
"""
Test script for the insider buying screener.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from screeners.insider_buying import screen_for_insider_buying

def test_insider_buying_screener():
    """Test the insider buying screener with a small universe."""
    
    # Create a small test universe with some well-known stocks
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMZN']
    test_universe = pd.DataFrame({
        'symbol': test_symbols,
        'security': [f'Test Company {s}' for s in test_symbols],
        'gics_sector': ['Technology'] * len(test_symbols)
    })
    
    print("Testing insider buying screener...")
    print(f"Test universe: {test_symbols}")
    
    try:
        # Run the screener with a lower threshold for testing
        results = screen_for_insider_buying(test_universe, min_buying_score=30.0, lookback_days=90)
        
        print(f"\nResults returned: {len(results)} stocks")
        
        if len(results) > 0:
            print("\nResults:")
            print(results[['symbol', 'company_name', 'buying_score', 'total_trades', 'buy_trades', 'sell_trades', 'meets_threshold']].to_string(index=False))
            
            # Show top 3 detailed results
            if len(results) >= 3:
                print(f"\nTop 3 detailed results:")
                for i in range(min(3, len(results))):
                    row = results.iloc[i]
                    print(f"\n{i+1}. {row['symbol']} - {row['company_name']}")
                    print(f"   Buying Score: {row['buying_score']:.1f}/100")
                    print(f"   Total Trades: {row['total_trades']}")
                    print(f"   Buy/Sell: {row['buy_trades']} buys, {row['sell_trades']} sells")
                    print(f"   Net Shares: {row['net_shares']:,}")
                    print(f"   Unique Insiders: {row['unique_insiders']}")
                    print(f"   Recent Spike: {row['recent_activity_spike']}")
                    print(f"   Meets Threshold: {row['meets_threshold']}")
        else:
            print("No stocks with insider buying activity found in test universe")
            print("This might be expected if there's no recent insider activity for these symbols")
            
    except Exception as e:
        print(f"Error running screener: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_insider_buying_screener()
