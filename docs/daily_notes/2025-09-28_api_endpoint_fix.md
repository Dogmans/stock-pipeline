# API Endpoint Fix Documentation - September 28, 2025

## Issue Discovered
The switch from FMP v4 API to stable API revealed a critical architectural difference:

### v4 API Behavior:
- General search returns chronological insider trades across all stocks
- Pagination captures older trades for any symbol

### Stable API Behavior:
- General search returns only the most recent trades across all stocks
- Older trades for specific symbols require symbol-specific queries
- RAPP's September purchases don't appear in general pagination

## Root Cause Analysis

**RAPP Test Results:**
- Stable API symbol-specific query: ✅ Returns 47 RAPP trades, 15 recent
- Stable API general search: ❌ Returns 0 RAPP trades in first 1000 records
- September purchases ($1.6M) are detected in symbol-specific query

## Solutions

### Option 1: Hybrid Approach (Recommended)
1. Use general search for high-activity stocks (captures most recent insider activity)
2. Use symbol-specific queries for a subset of target universe
3. Focus on stocks with recent price/volume changes that might correlate with insider activity

### Option 2: Targeted Screening 
1. Pre-filter universe based on technical indicators
2. Run symbol-specific insider queries only on promising candidates
3. Reduces API calls while maintaining coverage

### Option 3: Multi-Phase Screening
1. Phase 1: General search identifies actively traded stocks
2. Phase 2: Symbol-specific search on remaining universe sample
3. Phase 3: Technical analysis integration

## Implementation Status

**Fixed Issues:**
✅ Field name spelling: `acquisitionOrDisposition` vs `acquistionOrDisposition`
✅ API endpoint: stable vs v4
✅ Data availability confirmed for RAPP

**Remaining Challenge:**
❌ General search doesn't capture all insider activity
❌ Need architectural change for comprehensive coverage

## Recommendation

For immediate fix: Implement Option 1 (Hybrid Approach)
- Use general search to capture high-activity stocks
- Add symbol-specific queries for Russell 2000 companies with recent technical signals
- This balances API efficiency with comprehensive coverage

**Key Learning:** Different insider trading APIs have different pagination and filtering behaviors. Always test with known cases when switching endpoints.
