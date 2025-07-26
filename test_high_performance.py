import pandas as pd
from screeners.combined import screen_for_high_performance

# Test the high_performance combined screener
print("Testing high_performance combined screener...")

try:
    # Get a small universe for testing
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']
    test_df = pd.DataFrame({'symbol': test_symbols})
    
    # Run the high_performance combination
    result_df = screen_for_high_performance(test_df)
    
    print(f"High performance screener returned {len(result_df)} results")
    
    if not result_df.empty:
        print(f"\n🎉 SUCCESS! Found {len(result_df)} stocks that passed all three high-performance criteria:")
        print("="*80)
        for _, row in result_df.iterrows():
            print(f"• {row['company_name']} ({row['symbol']})")
            print(f"  Sector: {row['sector']}")
            print(f"  Metrics: {row['metrics_summary']}")
            print(f"  Reason: {row['reason']}")
            print()
    else:
        print("No stocks passed all three criteria in the test set.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
