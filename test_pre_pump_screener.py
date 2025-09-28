#!/usr/bin/env python3
"""Test script for enhanced pre-pump insider buying screener."""

from screeners.insider_buying import screen_for_insider_buying
import pandas as pd

def test_pre_pump_screener():
    """Test the enhanced pre-pump screener."""
    # Test with a small sample
    test_df = pd.DataFrame({
        'symbol': ['ORCL', 'META', 'AAPL'], 
        'security': ['Oracle Corp', 'Meta Platforms', 'Apple Inc'], 
        'gics_sector': ['Technology', 'Technology', 'Technology']
    })
    
    print('Testing enhanced pre-pump screener...')
    results = screen_for_insider_buying(test_df, min_buying_score=60.0, lookback_days=60)
    print(f'Results: {len(results)} stocks analyzed')
    
    if not results.empty:
        print('\nTop results:')
        for _, row in results.head(3).iterrows():
            print(f'{row["symbol"]}: Pre-pump score {row["buying_score"]:.1f}, '
                  f'Technical: {row["technical_score"]:.1f}, '
                  f'Acceleration: {row["acceleration_score"]:.1f}, '
                  f'Consolidation: {row["consolidation_detected"]}')
    else:
        print('No results found')

if __name__ == '__main__':
    test_pre_pump_screener()
