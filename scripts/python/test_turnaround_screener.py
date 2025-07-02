# Test Turnaround Screener Script
# This script tests the turnaround screener on different universes
# and saves the results to CSV files.

# Import required modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
# Updated import to use new screeners package structure
from screeners.turnaround_candidates import screen_for_turnaround_candidates
import universe
import pandas as pd
import os
import time

# Create output directory if it doesn't exist
os.makedirs('output/turnaround_analysis', exist_ok=True)

# Track timing
start_time = time.time()

print("Testing turnaround screener...")

# Test on S&P 500
print("\nRunning on S&P 500 universe...")
sp500 = universe.get_sp500_universe()
sp500_results = screen_for_turnaround_candidates(sp500)
print(f"Found {len(sp500_results)} turnaround candidates in S&P 500")

if not sp500_results.empty:
    sp500_results.to_csv('output/turnaround_analysis/sp500_turnarounds.csv', index=False)
    print("Results saved to 'output/turnaround_analysis/sp500_turnarounds.csv'")
    
    # Display found candidates
    print("\nS&P 500 Turnarounds:")
    print(sp500_results[['symbol', 'name', 'sector', 'primary_factor', 'turnaround_score']])

# Test on Russell 2000 (if available)
try:
    print("\nRunning on Russell 2000 universe...")
    russell = universe.get_russell2000_universe()
    
    # Sample 200 stocks from Russell to manage API calls
    russell_sample = russell.sample(min(200, len(russell)))
    print(f"Testing on {len(russell_sample)} stocks from Russell 2000...")
    
    russell_results = screen_for_turnaround_candidates(russell_sample)
    print(f"Found {len(russell_results)} turnaround candidates in Russell 2000 sample")
    
    if not russell_results.empty:
        russell_results.to_csv('output/turnaround_analysis/russell_turnarounds.csv', index=False)
        print("Results saved to 'output/turnaround_analysis/russell_turnarounds.csv'")
        
        # Display found candidates
        print("\nRussell 2000 Turnarounds:")
        print(russell_results[['symbol', 'name', 'sector', 'primary_factor', 'turnaround_score']])
except Exception as e:
    print(f"Error processing Russell 2000: {e}")

# Get total runtime
end_time = time.time()
runtime = end_time - start_time
print(f"\nTotal runtime: {runtime:.2f} seconds")

# Combine all results
print("\nCombining results...")
all_results = pd.DataFrame()
if not sp500_results.empty:
    sp500_results['universe'] = 'S&P 500'
    all_results = pd.concat([all_results, sp500_results])
    
if 'russell_results' in locals() and not russell_results.empty:
    russell_results['universe'] = 'Russell 2000'
    all_results = pd.concat([all_results, russell_results])
    
if not all_results.empty:
    # Sort by score descending
    all_results = all_results.sort_values('turnaround_score', ascending=False)
    all_results.to_csv('output/turnaround_analysis/all_turnarounds.csv', index=False)
    print(f"Combined {len(all_results)} results saved to 'output/turnaround_analysis/all_turnarounds.csv'")
    
    # Summary by score
    print("\nScore Distribution:")
    print(all_results['turnaround_score'].value_counts().sort_index(ascending=False))
    
    # Summary by primary factor
    print("\nPrimary Factor Distribution:")
    print(all_results['primary_factor'].value_counts())
    
    # Summary by sector
    print("\nSector Distribution:")
    print(all_results['sector'].value_counts())
else:
    print("No turnaround candidates found in any universe.")

print("\nTest completed successfully.")
