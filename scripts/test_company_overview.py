"""
Test script for the updated get_company_overview method in FinancialModelingPrepProvider.

Run this script to test the enhanced company overview data collection that
aggregates data from multiple FMP API endpoints.
"""
import sys
import os
import pandas as pd
import json
from pprint import pprint
import logging

# Add the project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging to only show warnings and above
logging.basicConfig(level=logging.WARNING)

# Import the provider
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider

def format_value(value):
    """Format values for better display"""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Format numeric values
        if isinstance(value, float):
            return f"{value:,.2f}"
        else:
            return f"{value:,}"
    return value

def test_company_overview():
    """
    Test the enhanced get_company_overview method that collects data from multiple endpoints.
    """
    # Initialize the provider
    provider = FinancialModelingPrepProvider()
    
    # Test with well-known stocks from different sectors
    test_symbols = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'JPM', 'JNJ']
    
    # Create a table for results
    results = []
    
    # Test each symbol and collect results
    for symbol in test_symbols:
        print(f"\nTesting {symbol}...")
        try:
            # Force refresh to ensure we get the latest data
            overview = provider.get_company_overview(symbol, force_refresh=True)
            
            # Extract key metrics we're interested in
            key_metrics = [
                'Symbol', 'Name', 'MarketCapitalization', 'PERatio', 'EPS',
                'Beta', '52WeekHigh', '52WeekLow', 'LastDividendDate',
                'PriceToBookRatio', 'PriceToSalesRatio', 'DataCompleteness'
            ]
            
            metrics_dict = {k: overview.get(k, 'N/A') for k in key_metrics}
            results.append(metrics_dict)
            
            # Check for missing metrics
            missing = [k for k in key_metrics if k not in overview or not overview[k]]
            if missing and 'DataCompleteness' not in missing:
                print(f"  Warning: Missing metrics for {symbol}: {missing}")
            
        except Exception as e:
            print(f"  Error testing {symbol}: {e}")
    
    # Display results in a well-formatted table
    print("\n\n============== RESULTS SUMMARY ==============\n")
    
    # Convert results to DataFrame for better display
    results_df = pd.DataFrame(results)
    
    # Format numeric columns
    for col in ['MarketCapitalization', 'PERatio', 'EPS', 'Beta', 
                '52WeekHigh', '52WeekLow', 'PriceToBookRatio', 'PriceToSalesRatio']:
        if col in results_df.columns:
            results_df[col] = results_df[col].apply(format_value)
    
    # Print the table
    print(results_df.to_string(index=False))
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_company_overview()
