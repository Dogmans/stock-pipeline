#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

# Test that all screeners can be imported and used
print("Testing all screeners after circular import fix...")

import pandas as pd

# Test import of PE Ratio screener specifically
try:
    from screeners.pe_ratio import PERatioScreener
    print("✅ PERatioScreener imported successfully")
    
    # Test basic functionality
    screener = PERatioScreener()
    print(f"✅ PERatioScreener instantiated: {screener.get_strategy_name()}")
    
except Exception as e:
    print(f"❌ PERatioScreener failed: {e}")

# Test import via screeners module
try:
    from screeners import PERatioScreener as PEScreener2
    print("✅ PERatioScreener imported via screeners module")
except Exception as e:
    print(f"❌ PERatioScreener via screeners module failed: {e}")

# Test analyst sentiment screener
try:
    from screeners.analyst_sentiment_momentum import AnalystSentimentMomentumScreener
    sentiment_screener = AnalystSentimentMomentumScreener()
    print(f"✅ AnalystSentimentMomentumScreener working: {sentiment_screener.get_strategy_name()}")
except Exception as e:
    print(f"❌ AnalystSentimentMomentumScreener failed: {e}")

# Test screener registry
try:
    from utils import get_screener, list_screeners
    print("✅ Screener registry functions imported")
    
    # This will trigger auto-registration if needed
    screeners = list_screeners()
    print(f"✅ Found {len(screeners)} registered screeners")
    
    # Test getting specific screener
    pe_screener = get_screener("pe_ratio")
    if pe_screener:
        print("✅ PE Ratio screener retrieved from registry")
    else:
        print("❌ PE Ratio screener not found in registry")
        
except Exception as e:
    print(f"❌ Screener registry failed: {e}")

print("All tests completed!")