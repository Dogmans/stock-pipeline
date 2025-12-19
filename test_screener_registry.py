#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

# Test that the screener registry works and can find all screeners
print("Testing screener registry functionality...")

try:
    from utils import get_screener, list_screeners
    
    print("1. Testing list_screeners...")
    screeners = list_screeners()
    print(f"   Found {len(screeners)} registered screeners: {list(screeners.keys())}")
    
    print("2. Testing get_screener for pe_ratio...")
    pe_screener = get_screener("pe_ratio")
    if pe_screener:
        print(f"   ✅ PE Ratio screener: {pe_screener.__class__.__name__}")
    else:
        print("   ❌ PE Ratio screener not found")
    
    print("3. Testing get_screener for analyst_sentiment_momentum...")
    sentiment_screener = get_screener("analyst_sentiment_momentum")
    if sentiment_screener:
        print(f"   ✅ Analyst Sentiment screener: {sentiment_screener.__class__.__name__}")
    else:
        print("   ❌ Analyst Sentiment screener not found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("Registry test completed.")