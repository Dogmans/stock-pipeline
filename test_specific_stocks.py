#!/usr/bin/env python3
"""
Test script to verify specific stocks like ANR are being filtered out.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
import pandas as pd

def test_specific_stocks():
    """Test specific stocks mentioned in the Russell 2000 report."""
    
    # Test stocks that showed P/B = 0.00 in the report
    test_symbols = ['INR', 'EML', 'CWCO', 'ASPI', 'SCWO', 'NXXT', 'HROW', 'REFI', 'ZYME', 'CWST']
    
    provider = FinancialModelingPrepProvider()
    
    print("Testing stocks that showed P/B = 0.00 in Russell 2000 report...")
    
    for symbol in test_symbols:
        print(f"\n=== Testing {symbol} ===")
        
        try:
            # Get company overview data
            company_data = provider.get_company_overview(symbol)
            
            if company_data:
                pb_ratio = company_data.get('PriceToBookRatio')
                print(f"API returned PriceToBookRatio: {pb_ratio} (type: {type(pb_ratio)})")
                
                # Test our updated filtering logic
                if pb_ratio is None or pb_ratio <= 0 or pb_ratio < 0.01:
                    print(f"✓ {symbol} would be FILTERED OUT (pb_ratio = {pb_ratio})")
                else:
                    print(f"✗ {symbol} would be INCLUDED (pb_ratio = {pb_ratio})")
                    
            else:
                print("No company data returned")
                
        except Exception as e:
            print(f"Error getting data for {symbol}: {e}")

if __name__ == "__main__":
    test_specific_stocks()
