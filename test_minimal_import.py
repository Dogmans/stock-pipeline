#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

# Test imports one by one to isolate the issue
print("Testing individual screener imports...")

try:
    print("1. Testing base_screener import...")
    from screeners.base_screener import BaseScreener
    print("   ✅ base_screener imported successfully")
except Exception as e:
    print(f"   ❌ base_screener failed: {e}")

try:
    print("2. Testing pe_ratio import...")
    from screeners.pe_ratio import PERatioScreener
    print("   ✅ pe_ratio imported successfully")
except Exception as e:
    print(f"   ❌ pe_ratio failed: {e}")

try:
    print("3. Testing analyst_sentiment_momentum import...")
    from screeners.analyst_sentiment_momentum import AnalystSentimentMomentumScreener
    print("   ✅ analyst_sentiment_momentum imported successfully")
except Exception as e:
    print(f"   ❌ analyst_sentiment_momentum failed: {e}")

try:
    print("4. Testing screeners __init__ import...")
    from screeners import PERatioScreener
    print("   ✅ screeners __init__ imported successfully")
except Exception as e:
    print(f"   ❌ screeners __init__ failed: {e}")

print("Import test completed.")