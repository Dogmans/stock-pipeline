# Testing the Turnaround Screener

This document describes the testing approach for the turnaround candidate screener.

## Unit Tests

We use two main test files to validate the turnaround screener functionality:

1. `tests/test_turnaround_screener.py`: Tests the full implementation with mocked API responses
2. `tests/test_turnaround_screener_logic.py`: Tests the core logic with simplified mock data

### Running the Tests

```powershell
# Run all tests
python -m unittest discover -s tests

# Run specific test files
python -m unittest tests/test_turnaround_screener.py
python -m unittest tests/test_turnaround_screener_logic.py

# Run with coverage
python -m coverage run -m unittest tests/test_turnaround_screener_logic.py
python -m coverage report -m

# Generate HTML coverage report
python -m coverage html
```

## Test Cases Overview

### Core Logic Tests

The `test_turnaround_screener_logic.py` file focuses on testing the detection logic with controlled mock data:

1. **True Turnaround Detection**
   - Tests detection of negative→positive EPS transitions
   - Validates revenue recovery pattern recognition
   - Confirms balance sheet improvement detection (cash/debt trends)

2. **Non-Turnaround Detection**
   - Tests that steady growth companies are NOT flagged as turnarounds
   - Ensures the threshold score prevents false positives

### Full Implementation Tests

The `test_turnaround_screener.py` file tests the complete screener including:

1. **API Integration Tests**
   - Tests proper handling of API responses
   - Validates field mapping from API to internal models
   - Tests error handling for missing data

2. **Scoring System Tests**
   - Verifies correct score calculation
   - Tests that only companies meeting the threshold are returned
   - Validates primary factor identification logic

3. **Cache Management Tests**
   - Tests force_refresh parameter correctly bypasses cache
   - Verifies cache is used when appropriate

## Mock Data Patterns

### Turnaround Pattern

```python
# Mock income statement with EPS going from negative to positive
mock_income = pd.DataFrame({
    'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
    'eps': [-0.40, -0.30, -0.20, -0.10, 0.05, 0.15, 0.25, 0.35],
    'revenue': [80, 85, 90, 95, 100, 105, 110, 120],
    'grossProfit': [16, 18, 20, 22, 25, 28, 31, 36]
})
# Reverse to have most recent first
mock_income = mock_income.iloc[::-1].reset_index(drop=True)

# Mock balance sheet with improving cash and reducing debt
mock_balance = pd.DataFrame({
    'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
    'cash': [50, 48, 45, 40, 38, 35, 33, 30],
    'totalDebt': [100, 105, 110, 120, 125, 130, 120, 110]
})
# Reverse to have most recent first
mock_balance = mock_balance.iloc[::-1].reset_index(drop=True)
```

### Non-Turnaround Pattern

```python
# Mock income statement with steadily positive EPS
mock_income = pd.DataFrame({
    'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
    'eps': [0.40, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47],
    'revenue': [100, 101, 102, 103, 104, 105, 106, 107],
    'grossProfit': [25, 25, 25, 25, 25, 25, 25, 25]
})
# Reverse to have most recent first
mock_income = mock_income.iloc[::-1].reset_index(drop=True)

# Mock balance sheet with steady metrics
mock_balance = pd.DataFrame({
    'fiscalDateEnding': pd.date_range(end='2025-03-31', periods=8, freq='Q'),
    'cash': [50, 50, 50, 50, 50, 50, 50, 50],
    'totalDebt': [100, 100, 100, 100, 100, 100, 100, 100]
})
# Reverse to have most recent first
mock_balance = mock_balance.iloc[::-1].reset_index(drop=True)
```

## Validation Workflow

1. Run unit tests with different mock data patterns
2. Test with actual S&P 500 universe (expect few or no turnarounds)
3. Test with Russell 2000 universe (expect more potential turnarounds)
4. Manually verify that detected turnarounds match the expected criteria

## Edge Cases

The tests also cover these edge cases:

1. Missing financial data (some API fields not available)
2. Companies with fewer than 8 quarters of data
3. Division by zero scenarios (zero revenue, etc.)
4. Extreme values in financial data
5. Borderline scoring cases (exactly at threshold)

## Debugging Test Failures

If tests fail, check these common issues:

1. Field name changes in the API response structure
2. Changes in the scoring thresholds
3. Cache issues (run with force_refresh=True)
4. Missing or corrupt mock data
