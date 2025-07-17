# Stock Screener Methods

This document provides detailed information about the various stock screening methods implemented in the pipeline.

## Turnaround Candidate Detection

The pipeline implements a sophisticated approach to identify companies that have genuinely "turned the corner" from financial difficulties, as opposed to those simply showing steady growth.

### Key Detection Patterns

1. **EPS Turnaround Detection**
   ```python
   def detect_eps_turnaround(income_df):
       """Detect if EPS shows a turnaround pattern"""
       eps_data = income_df['eps'].iloc[:8].values
       
       # Check if there's a negative to positive transition
       if any(eps_data[-4:] > 0) and any(eps_data[0:4] < 0):
           return "Negative→Positive EPS", 3
           
       # Check for significant improvement
       if len(eps_data) >= 8:
           eps_growth = (eps_data[0] - eps_data[4]) / abs(eps_data[4]) if eps_data[4] != 0 else 0
           if eps_growth > 0.5:  # 50% improvement
               return "Strong EPS Recovery", 2
               
       return None, 0
   ```

2. **Revenue Recovery Pattern**
   ```python
   def detect_revenue_turnaround(income_df):
       """Detect if revenue shows a recovery pattern"""
       # Calculate YoY revenue growth rates
       revenue = income_df['revenue'].iloc[:8].values
       
       if len(revenue) >= 8:
           # Check for transition from negative to positive growth
           growth_rates = [(revenue[i] - revenue[i+4]) / revenue[i+4] for i in range(4)]
           if any(r < 0 for r in growth_rates[2:]) and all(r > 0 for r in growth_rates[:2]):
               return "Revenue Recovery", 2
       
       return None, 0
   ```

3. **Margin Improvement**
   ```python
   def detect_margin_recovery(income_df):
       """Detect if margins show a recovery pattern"""
       if 'revenue' not in income_df.columns or 'grossProfit' not in income_df.columns:
           return None, 0
           
       # Calculate gross margins for last 8 quarters
       revenue = income_df['revenue'].iloc[:8].values
       gross_profit = income_df['grossProfit'].iloc[:8].values
       
       # Calculate margin percentages
       margins = np.array([gp/rev if rev > 0 else 0 for gp, rev in zip(gross_profit, revenue)])
       
       if len(margins) >= 8:
           # Find lowest margin in quarters 4-8
           past_min_idx = 4 + np.argmin(margins[4:8])
           past_min = margins[past_min_idx]
           
           # Check if recent margins show recovery from minimum
           recent_margins = margins[:4]
           if any(m > past_min * 1.1 for m in recent_margins):  # 10% improvement
               pct_increase = ((np.mean(recent_margins) / past_min) - 1) * 100
               return f"Margin Recovery (+{pct_increase:.1f}%)", 2
               
       return None, 0
   ```

4. **Balance Sheet Improvement**
   ```python
   def detect_balance_sheet_improvement(balance_df):
       """Detect if balance sheet is showing turnaround signs"""
       score = 0
       reason = []
       
       # Check cash trend
       if 'cash' in balance_df.columns:
           cash = balance_df['cash'].iloc[:8].values
           if len(cash) >= 8:
               past_trend = np.polyfit(range(4), cash[4:8], 1)[0]
               recent_trend = np.polyfit(range(4), cash[0:4], 1)[0]
               
               if past_trend < 0 and recent_trend > 0:
                   reason.append("Cash Recovery")
                   score += 2
       
       # Check debt trend
       if 'totalDebt' in balance_df.columns:
           debt = balance_df['totalDebt'].iloc[:8].values
           if len(debt) >= 8:
               past_trend = np.polyfit(range(4), debt[4:8], 1)[0]
               recent_trend = np.polyfit(range(4), debt[0:4], 1)[0]
               
               if past_trend > 0 and recent_trend < 0:
                   reason.append("Debt Reduction")
                   score += 2
                   
       return ", ".join(reason) if reason else None, score
   ```

### Scoring System

Turnaround candidates are scored based on multiple factors:

```python
# Determine overall score and primary factor
overall_score = eps_score + revenue_score + margin_score + balance_sheet_score

# Only consider as turnaround if score exceeds threshold
if overall_score >= 5:
    # Find primary factor
    factors = [
        (eps_reason, eps_score),
        (revenue_reason, revenue_score),
        (margin_reason, margin_score),
        (balance_sheet_reason, balance_sheet_score)
    ]
    
    # Get the highest-scoring factor
    primary_factor = max((r for r in factors if r[0]), key=lambda x: x[1])[0]
    
    result_df = pd.DataFrame({
        'symbol': [symbol],
        'name': [company_name],
        'sector': [sector],
        'turnaround_score': [overall_score],
        'primary_factor': [primary_factor],
        'eps_trend': [eps_reason],
        'revenue_trend': [revenue_reason],
        'margin_trend': [margin_reason],
        'balance_sheet': [balance_sheet_reason],
        'reason': [f"Score: {overall_score}"]
    })
    
    return result_df
```

### Usage Example

To run the turnaround screener against a universe of stocks:

```python
from screeners import screen_for_turnaround_candidates
import universe

# Get universe
sp500 = universe.get_sp500_universe()

# Run turnaround screener
results = screen_for_turnaround_candidates(sp500)

# Display results
print(f"Found {len(results)} turnaround candidates")
print(results[['symbol', 'name', 'primary_factor', 'turnaround_score']])
```

### Common Patterns for Turnaround Candidates

The ideal turnaround candidate shows these patterns:

1. **EPS Pattern**:
   - From negative to positive (e.g., -$0.25 → -$0.15 → -$0.05 → +$0.10 → +$0.25)
   - Or significant improvement in positive EPS after a difficult period

2. **Revenue Pattern**:
   - Return to growth after decline (e.g., -5% → -2% → +3% → +8%)
   - Or significant acceleration in growth rate

3. **Margin Pattern**:
   - Bottomed out and now recovering (e.g., 15% → 12% → 10% → 13% → 16%)
   - Consistent improvement in recent quarters

4. **Balance Sheet Pattern**:
   - Cash: Previously declining, now growing
   - Debt: Previously increasing, now decreasing or stabilizing
   - Improving debt-to-equity ratio

### Implementation Notes

1. **Cache Management**:
   - Financial data is cached to minimize API calls
   - Force refresh parameter allows bypassing the cache when needed:
   ```python
   # To force fresh data
   results = screen_for_turnaround_candidates(universe_df, force_refresh=True)
   ```

2. **Error Handling**:
   - Robust checks for required fields in the API response
   - Fallback options when certain financial data is missing

3. **Performance Considerations**:
   - Processes one stock at a time to avoid memory issues with large universes
   - Uses vectorized operations where possible for efficiency

## Sharpe Ratio Screener

The Sharpe ratio screener identifies stocks with superior risk-adjusted returns by calculating the Sharpe ratio for each stock based on historical price performance.

### Sharpe Ratio Calculation

The Sharpe ratio measures risk-adjusted return and is calculated as:
```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility
```

### Implementation Details

1. **Historical Data Requirements**:
   - Minimum 252 trading days of price data (1 year)
   - Uses daily closing prices for return calculations

2. **Key Components**:
   ```python
   # Calculate daily returns
   daily_returns = historical_prices.pct_change().dropna()
   
   # Annualized portfolio return
   portfolio_return = (historical_prices.iloc[-1] / historical_prices.iloc[0] - 1) * 100
   
   # Annualized volatility
   portfolio_volatility = daily_returns.std() * np.sqrt(252)
   
   # Sharpe ratio calculation
   sharpe_ratio = (portfolio_return - risk_free_rate) / (portfolio_volatility * 100)
   ```

3. **Risk-Free Rate**:
   - Uses 10-year Treasury rate (currently ~4.5%)
   - Configurable via `RISK_FREE_RATE` in config

4. **Configuration**:
   - Threshold: `SHARPE_RATIO_THRESHOLD = 1.0` (configurable)
   - Higher threshold = more selective screening
   - Typical good Sharpe ratios: > 1.0, excellent: > 2.0

### Screening Criteria

- **Minimum Sharpe Ratio**: 1.0 (default)
- **Data Quality**: Must have sufficient trading history
- **Volatility Floor**: Prevents division by zero with extremely stable stocks

### Usage Example

```python
# Run Sharpe ratio screener
python main.py --universe sp500 --strategies sharpe_ratio

# Combine with other strategies
python main.py --universe sp500 --strategies value,sharpe_ratio
```

### Interpretation

- **Sharpe Ratio > 1.0**: Good risk-adjusted performance
- **Sharpe Ratio > 1.5**: Very good risk-adjusted performance  
- **Sharpe Ratio > 2.0**: Excellent risk-adjusted performance
- **High Sharpe + Low Volatility**: Consistent performers
- **High Sharpe + High Volatility**: High-risk, high-reward stocks

### Performance Considerations

- **API Intensive**: Requires historical price data for each stock
- **Cache Friendly**: Reuses existing price data when available
- **Rate Limited**: Execution time depends on API rate limits

## Future Enhancements

Potential improvements to the turnaround detection:

1. **Additional Metrics**:
   - Include analyst estimate beats after previous misses
   - Add FCF (Free Cash Flow) improvement detection
   - Track inventory and accounts receivable trends

2. **Pattern Recognition**:
   - Add price pattern recognition to identify bottoming patterns
   - Incorporate relative strength vs. industry peers
   - Consider sector-specific turnaround metrics

3. **Advanced Scoring**:
   - Implement machine learning to identify successful historical turnarounds
   - Weight factors based on sector-specific importance
   - Add time-based decay to give more weight to recent improvements

### Sharpe Ratio Enhancements

1. **Advanced Risk Metrics**:
   - Implement Beta calculation for market-relative risk
   - Add Alpha calculation for excess returns
   - Include Maximum Drawdown analysis

2. **Portfolio-Level Analysis**:
   - Calculate portfolio Sharpe ratio for combined positions
   - Implement correlation analysis between selected stocks
   - Add sector-relative Sharpe ratio comparisons

3. **Time-Series Analysis**:
   - Rolling Sharpe ratio calculations for trend analysis
   - Seasonal adjustment for cyclical stocks
   - Volatility clustering detection
