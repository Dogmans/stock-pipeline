#!/usr/bin/env python3
"""
Test script to verify data provider prioritization.

This script creates a MultiProvider instance and displays the order 
of providers it tries when fetching data.
"""
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path if running script directly
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

import data_providers
from utils import setup_logging

# Set up logger
logger = setup_logging()

def test_provider_priority():
    """Test the priority order of providers in the MultiProvider."""
    print("Testing Data Provider Priority\n")
    
    # Create a MultiProvider instance
    multi_provider = data_providers.get_provider('multi')
    
    # Print the order of providers
    print("Providers will be tried in the following order:")
    for i, provider in enumerate(multi_provider.providers):
        print(f"{i+1}. {provider.get_provider_name()}")
    
    # Print info about each provider
    print("\nProvider Details:")
    for i, provider in enumerate(multi_provider.providers):
        provider_name = provider.get_provider_name()
        print(f"\n{provider_name}:")
        
        # Try to get rate limits info if available
        rate_limit = getattr(provider, 'RATE_LIMIT', 'Not specified')
        daily_limit = getattr(provider, 'DAILY_LIMIT', 'Not specified')
        print(f"  Rate Limit: {rate_limit} calls/minute")
        print(f"  Daily Limit: {daily_limit} calls/day")
    
    # Try to fetch some basic data
    print("\nTesting API access...")
    try:
        # Try to get Apple's company overview using the multi provider
        overview = multi_provider.get_company_overview("AAPL")
        if overview:
            provider_used = overview.get('_provider_used', 'Unknown')
            print(f"\nSuccessfully retrieved AAPL company data using: {provider_used}")
        else:
            print("\nFailed to retrieve company data")
    except Exception as e:
        print(f"\nError retrieving data: {e}")

if __name__ == "__main__":
    test_provider_priority()
