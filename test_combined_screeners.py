"""
Test script for the new combined screeners system.
Tests multiple combined screener configurations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from config import CombinedScreeners

def test_combined_screeners():
    """Test the new combined screeners system."""
    print("Testing Combined Screeners System...")
    print("=" * 50)
    
    # Display available combinations
    print("Available Combined Screener Configurations:")
    combinations = CombinedScreeners.get_all_combinations()
    
    for key, config in combinations.items():
        print(f"\n{key.upper()}:")
        print(f"  Name: {config['name']}")
        print(f"  Description: {config['description']}")
        print(f"  Strategies: {', '.join(config['strategies'])}")
    
    print("\n" + "=" * 50)
    
    # Test the configuration system
    print("\nTesting Configuration System:")
    
    # Test getting a specific combination
    high_perf = CombinedScreeners.get_combination('high_performance')
    if high_perf:
        print(f"✓ Retrieved 'high_performance' combination: {high_perf['name']}")
        print(f"  Strategies: {high_perf['strategies']}")
    else:
        print("✗ Failed to retrieve 'high_performance' combination")
    
    # Test getting all combinations
    all_combos = CombinedScreeners.get_all_combinations()
    print(f"✓ Retrieved {len(all_combos)} total combinations")
    
    print("\n" + "=" * 50)
    print("Combined screener system ready for testing with real data!")
    print("\nUsage examples:")
    print("python main.py --universe sp500 --strategies traditional_value")
    print("python main.py --universe sp500 --strategies high_performance")
    print("python main.py --universe sp500 --strategies comprehensive")
    print("python main.py --universe sp500 --strategies distressed_value")

if __name__ == "__main__":
    test_combined_screeners()
