#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

import pandas as pd
from screeners.analyst_sentiment_momentum import AnalystSentimentMomentumScreener

def test_screener_directly():
    """Test the screener directly with minimal setup."""
    
    print('Testing Analyst Sentiment Momentum Screener directly...')
    
    try:
        screener = AnalystSentimentMomentumScreener()
        
        # Test get_data_for_symbol directly
        print('Testing get_data_for_symbol for AAPL...')
        data = screener.get_data_for_symbol('AAPL')
        
        if data:
            print('Data retrieved successfully!')
            print(f'  Symbol: {data.get("symbol", "Unknown")}')
            print(f'  Company: {data.get("companyName", "Unknown")}')
            
            # Test calculate_score
            print('Testing calculate_score...')
            score = screener.calculate_score(data)
            print(f'  Score: {score}')
            
            if score is not None:
                # Test meets_threshold
                meets = screener.meets_threshold(score)
                print(f'  Meets threshold: {meets}')
                
                # Test reasoning generation
                analyst_data = data.get('analyst_data', {})
                reasoning = screener._generate_reasoning('AAPL', analyst_data, score)
                print(f'  Reasoning: {reasoning}')
            
        else:
            print('No data retrieved')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_screener_directly()