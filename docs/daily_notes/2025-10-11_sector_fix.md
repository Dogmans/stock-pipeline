# Sector Information Fix - 2025-10-11

## Issue Identified
Some screeners were displaying "Unknown" sectors in reports due to inconsistent field name usage for sector information.

## Root Cause
The `InsiderBuyingScreener` was using universe data's `'gics_sector'` field instead of the provider data's `'Sector'` field, which is the standard used by the BaseScreener and other screeners.

### Inconsistent Field Usage:
- **BaseScreener and most screeners**: Use `data.get('Sector', 'Unknown')` from provider data
- **InsiderBuyingScreener (before fix)**: Used `company_info['gics_sector']` from universe data
- **Problem**: When universe data doesn't have gics_sector populated, it falls back to 'Unknown'

## Solution Applied
Updated `screeners/insider_buying.py` line 108-109 to use provider data consistently:

**Before (incorrect):**
```python
company_info = universe_df[universe_df['symbol'] == symbol]
company_name = company_info['security'].iloc[0] if not company_info.empty else symbol
sector = company_info['gics_sector'].iloc[0] if not company_info.empty and 'gics_sector' in company_info.columns else 'Unknown'
```

**After (fixed):**
```python
company_info = universe_df[universe_df['symbol'] == symbol]
company_name = company_info['security'].iloc[0] if not company_info.empty else symbol
# Use provider data for sector (consistent with BaseScreener)
sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
```

## Data Source Consistency
- **Provider Data (`company_data`)**: Contains `'Sector'` field from Financial Modeling Prep API
- **Universe Data (`universe_df`)**: Contains `'gics_sector'` field from Wikipedia/iShares data
- **Standard Practice**: Use provider data's `'Sector'` field as it's more reliable and complete

## Validation Results
Tested with multiple screeners and confirmed all sectors display correctly:
- ✅ P/E Ratio Screener: Communication Services, Energy
- ✅ Insider Buying Screener: Consumer Cyclical, Real Estate  
- ✅ Fifty Two Week Lows Screener: Basic Materials, Consumer Cyclical, Healthcare

## Files Modified
- `screeners/insider_buying.py`: Updated sector field access to use provider data

## Prevention
All screeners that override the base `screen_stocks` method should use:
```python
sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
```

This ensures consistency with the BaseScreener template and reliable sector information in reports.