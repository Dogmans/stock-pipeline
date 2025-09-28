# CRITICAL BUG FIX - Insider Buying Methodology

Date: 2025-09-28
Issue: **Option Exercises Incorrectly Counted as Insider Purchases**

## Problem Discovered

User questioned MPAA showing 44.8/100 score with "11 buy trades vs 0 sells" in Russell 2000 screening. Investigation revealed:

### Root Cause: Option Exercises ≠ Insider Buying

**What we were incorrectly counting:**
- **A-M-Exempt** transactions with **$0.00 price** = Option exercises
- These are NOT insider purchases with real money
- These are routine conversion of existing stock options to shares
- **No bullish signal** about company prospects

### Validation Against Public Data

**Finviz MPAA Data Confirmed:**
- Sept 24, 2025: All executives exercised options ($0.00 price)
- **Actual purchases with real money were months ago** (Nov 2024)

### The Fix Applied

**Before (WRONG):**
```python
if (acquisition == 'A' and 
    ('PURCHASE' in transaction_type or 
     'BUY' in transaction_type or
     ('EXEMPT' in transaction_type) or     # <- THIS WAS THE PROBLEM
     ('EXERCISE' in transaction_type))):   # <- AND THIS
```

**After (CORRECT):**
```python
price = trade.get('price', 0)

if (acquisition == 'A' and 
    ('PURCHASE' in transaction_type or 
     'BUY' in transaction_type)):
    # Must have actual price paid (not $0 option exercises)
    if price > 0 and not ('AWARD' in transaction_type or 'GRANT' in transaction_type):
```

## Impact of Fix

### MPAA Results:
- **Before**: 44.8/100 score, "11 buy trades vs 0 sells"
- **After**: 25.0/100 score, "0 buy trades vs 0 sells" ✅

### Screening Results:
- **Before**: Many false positives from option exercises
- **After**: Only genuine purchases with real money count ✅

## Methodology Now Correctly Identifies:

✅ **Actual Insider Purchases:**
- Open market purchases (A-P-Purchase)
- Private purchases (A-Buy) 
- **Only when price > $0**

❌ **Correctly Excludes:**
- Stock option exercises ($0 price)
- Stock awards and grants
- Compensation-related transactions

## Market Reality Validated

This fix confirms our earlier findings:
- **S&P 500**: Low insider buying numbers are genuine
- **Russell 2000**: Still shows more insider conviction than large caps
- **Methodology now accurately reflects real market conditions**

## Files Updated:
- `screeners/insider_buying.py` - Fixed transaction classification
- Documentation updated to reflect corrected methodology

## Key Takeaway:
**User's skepticism was absolutely justified!** The high scores were artificial due to counting routine option exercises as insider purchases. The corrected methodology now provides genuine insider buying signals.
