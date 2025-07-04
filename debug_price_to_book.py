#!/usr/bin/env python3
"""
Test script to debug the price-to-book ratio issue.
This will help us understand what data is being returned from the FMP API.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
import pandas as pd
import json

def debug_price_to_book():
    """Debug the price-to-book ratio data retrieval."""
    
    # Test symbols that are showing P/B = 0.00
    test_symbols = ['BATRA', 'SMID', 'SENEA', 'MLAB', 'KG']
    
    provider = FinancialModelingPrepProvider()
    
    for symbol in test_symbols:
        print(f"\n=== Testing {symbol} ===")
        
        try:
            # Get company overview data
            company_data = provider.get_company_overview(symbol)
            
            if company_data:
                print(f"Company Name: {company_data.get('Name', 'N/A')}")
                print(f"Sector: {company_data.get('Sector', 'N/A')}")
                print(f"Data Completeness: {company_data.get('DataCompleteness', 'N/A')}")
                
                # Focus on P/B ratio specifically
                pb_ratio = company_data.get('PriceToBookRatio')
                print(f"PriceToBookRatio: {pb_ratio} (type: {type(pb_ratio)})")
                
                # Check other ratios for comparison
                pe_ratio = company_data.get('PERatio')
                ps_ratio = company_data.get('PriceToSalesRatio')
                print(f"PERatio: {pe_ratio} (type: {type(pe_ratio)})")
                print(f"PriceToSalesRatio: {ps_ratio} (type: {type(ps_ratio)})")
                
                # Print full data for debugging
                print("Full company data:")
                for key, value in company_data.items():
                    print(f"  {key}: {value}")
                    
            else:
                print("No company data returned")
                
        except Exception as e:
            print(f"Error getting data for {symbol}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_price_to_book()
