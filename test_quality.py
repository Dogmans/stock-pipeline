import pandas as pd
from screeners import quality

# Test with a small set of stocks - create proper DataFrame
test_symbols = ['AAPL', 'MSFT', 'GOOGL']
test_df = pd.DataFrame({'symbol': test_symbols})
print('Testing quality screener with symbols:', test_symbols)

# Run the screener
try:
    result_df = quality.screen_for_quality(test_df)
    print(f'Quality screener returned {len(result_df)} results')
    if not result_df.empty:
        print('Quality screening results:')
        for _, row in result_df.iterrows():
            print(f"{row['symbol']}: Score {row['quality_score']}/10 - {row['reason']}")
    else:
        print('No stocks found')
except Exception as e:
    print(f'Quality screener error: {e}')
    import traceback
    traceback.print_exc()
