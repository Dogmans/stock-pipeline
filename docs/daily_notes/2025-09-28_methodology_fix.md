# Critical Methodology Fix - Insider Buying Screener

## Date: September 28, 2025

### Issue Identified
The insider buying screener was incorrectly classifying **stock compensation awards** as **actual insider purchases**, leading to inflated scores for companies with high executive compensation.

### Root Cause Analysis
**ORCL Example:**
- Original score: 51.0/100 with "2 buy trades"
- Reality: These were `A-Award` transactions worth $1.12B in **executive compensation**
- Not actual purchases with personal money showing insider confidence

### Transaction Type Analysis from FMP API
**Recent 60-day data:**
- `D-S-Sale`: 381 transactions (actual sales)
- `A-A-Award`: 209 transactions (stock compensation - NOT purchases)
- `A-P-Purchase`: 39 transactions (actual purchases with personal money)

### Methodology Correction Applied

**Before (Flawed):**
```python
# Incorrectly classified ALL "A" (Acquisition) transactions as buys
if (acquisition == 'A' or 
    'PURCHASE' in transaction_type or 
    'BUY' in transaction_type or
    ('EXERCISE' in transaction_type and acquisition == 'A')):
    buy_trades.append(trade)
```

**After (Corrected):**
```python
# Only consider ACTUAL PURCHASES (not awards/grants) as buying signals
if (acquisition == 'A' and 
    ('PURCHASE' in transaction_type or 
     'BUY' in transaction_type or
     ('EXEMPT' in transaction_type) or
     ('EXERCISE' in transaction_type))):
    # Exclude routine compensation awards and grants
    if not ('AWARD' in transaction_type or 'GRANT' in transaction_type):
        buy_trades.append(trade)
```

### Impact of Fix

**ORCL Results:**
- Before: 51.0/100 (2 "buy" trades - actually stock awards)
- After: 16.0/100 (0 actual buy trades) ✅

**FOX Results:**
- Before: 50.3/100 (19 "buy" trades - actually stock awards)
- After: 25.0/100 (0 actual buy trades) ✅

**Market-wide Impact:**
- 0 stocks now pass the 65.0/100 threshold (more realistic)
- Screener now correctly identifies actual insider conviction vs. routine compensation
- Eliminates false signals from high executive compensation packages

### Transaction Classification Guide

**TRUE Buying Signals:**
- `A-P-Purchase`: Open market purchases with personal money ✅
- `A-M-Exempt`: Private transactions (may indicate confidence) ✅
- `A-Exercise`: Option exercises (excluding grants) ✅

**NOT Buying Signals:**
- `A-A-Award`: Stock compensation awards ❌
- `A-G-Grant`: Stock grants ❌
- Any transaction with 'AWARD' or 'GRANT' in type ❌

### Validation
The corrected methodology now aligns with public insider trading data and properly distinguishes between:
1. **Routine compensation** (awards, grants) - Not indicative of confidence
2. **Actual purchases** (personal money invested) - True buying signals

This fix ensures the screener provides accurate signals for genuine insider confidence rather than inflated scores from executive compensation packages.
