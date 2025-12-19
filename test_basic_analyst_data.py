#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

# Test just the basic functionality without full import hierarchy
import pandas as pd
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider

def test_basic_analyst_data():
    """Test basic analyst data retrieval functionality."""
    
    print('Testing basic analyst data retrieval...')
    
    provider = FinancialModelingPrepProvider()
    
    # Test with AAPL
    symbol = 'AAPL'
    print(f'\nTesting {symbol}:')
    
    try:
        # Test analyst grades
        print('  Getting analyst grades...')
        grades = provider.get_analyst_grades(symbol, limit=5)
        print(f'    Grades data type: {type(grades)}')
        if isinstance(grades, pd.DataFrame) and not grades.empty:
            print(f'    Grades shape: {grades.shape}')
            print(f'    Sample grade columns: {list(grades.columns)}')
            if len(grades) > 0:
                print(f'    First grade sample: {grades.iloc[0].to_dict()}')
        elif isinstance(grades, list) and grades:
            print(f'    Sample grade keys: {list(grades[0].keys()) if len(grades) > 0 else "No grades"}')
        else:
            print('    No grades data available')
        
        # Test consensus
        print('  Getting consensus...')
        consensus = provider.get_analyst_grades_consensus(symbol)
        print(f'    Consensus data type: {type(consensus)}')
        print(f'    Consensus keys: {list(consensus.keys()) if consensus else "No consensus"}')
        
        print('Test completed successfully!')
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_basic_analyst_data()