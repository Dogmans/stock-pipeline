#!/usr/bin/env python3

from screeners.analyst_sentiment_momentum import AnalystSentimentMomentumScreener
import pandas as pd

def test_analyst_sentiment_screener():
    """Test the fixed analyst sentiment momentum screener."""
    
    print('Testing fixed Analyst Sentiment Momentum Screener...')
    screener = AnalystSentimentMomentumScreener()

    # Create small test universe
    test_universe = pd.DataFrame({'symbol': ['AAPL', 'MSFT']})
    print(f'Testing with {len(test_universe)} symbols')

    try:
        results = screener.screen_stocks(test_universe)
        print(f'Results: {len(results)} stocks found')
        
        if not results.empty:
            print('\nTop results:')
            for _, row in results.head().iterrows():
                symbol = row['symbol']
                score = row['score']
                reasoning = row.get('reasoning', 'No reasoning available')
                print(f'  {symbol}: Score {score:.1f} - {reasoning}')
        else:
            print('No stocks met criteria')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analyst_sentiment_screener()