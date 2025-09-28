#!/usr/bin/env python3
"""Test enhanced pre-pump screener with detailed scoring breakdown."""

from screeners.insider_buying import screen_for_insider_buying
import pandas as pd

def test_detailed_scoring():
    """Test the enhanced pre-pump screener with detailed scoring."""
    # Test with ORCL and FOX from our known results
    test_df = pd.DataFrame({
        'symbol': ['ORCL', 'FOX'], 
        'security': ['Oracle Corp', 'Fox Corp'], 
        'gics_sector': ['Technology', 'Communications']
    })
    
    print('Testing enhanced pre-pump screener with lower threshold...')
    results = screen_for_insider_buying(test_df, min_buying_score=30.0, lookback_days=60)
    
    if not results.empty:
        print('\nDetailed Pre-Pump Scoring Results:')
        print('='*60)
        for _, row in results.iterrows():
            print(f'{row["symbol"]}: Pre-pump score {row["buying_score"]:.1f}/100')
            insider_component = row["buying_score"] - row["technical_score"] - row["acceleration_score"]
            print(f'  - Insider component: {insider_component:.1f}/40')
            print(f'  - Technical score: {row["technical_score"]:.1f}/35') 
            print(f'  - Acceleration score: {row["acceleration_score"]:.1f}/25')
            print(f'  - Buy trades: {row["buy_trades"]}, Sell trades: {row["sell_trades"]}')
            print(f'  - Consolidation detected: {row["consolidation_detected"]}')
            print(f'  - Volume pattern score: {row["volume_pattern_score"]:.1f}')
            print(f'  - Recent activity spike: {row["recent_activity_spike"]}')
            print()
    else:
        print('No results found')

if __name__ == '__main__':
    test_detailed_scoring()
