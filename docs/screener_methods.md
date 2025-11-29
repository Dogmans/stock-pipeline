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

## Momentum Screener

The momentum screener identifies stocks with strong recent performance trends using weighted analysis of 6-month and 3-month returns.

### Implementation Details

1. **Momentum Score Calculation**:
   ```python
   # Weighted momentum score (6M: 60%, 3M: 40%)
   momentum_score = (six_month_return * 0.6) + (three_month_return * 0.4)
   ```

2. **Key Features**:
   - Default threshold: 15% momentum score
   - Configurable lookback periods
   - Sector and market cap analysis
   - Company fundamental integration

3. **Usage Example**:
   ```bash
   python main.py --universe sp500 --strategies momentum
   ```

## Quality Screener

Basic quality screening using a 10-point financial strength assessment.

### Scoring Components

1. **Profitability** (0-3 points)
2. **Financial Strength** (0-3 points) 
3. **Operational Efficiency** (0-2 points)
4. **Growth Stability** (0-2 points)

### Usage Example
```bash
python main.py --universe sp500 --strategies quality
```

## Enhanced Quality Screener

Advanced quality analysis with granular 0-100 point scoring across four dimensions.

### Scoring Components (0-100 Total)

1. **ROE Analysis** (0-25 points):
   - ROE > 15%: Full points
   - ROE 10-15%: Scaled scoring
   - ROE < 10%: Minimal points

2. **Profitability Analysis** (0-25 points):
   - Operating margin assessment
   - Profit margin evaluation
   - Trend analysis

3. **Financial Strength** (0-25 points):
   - Debt-to-equity ratio
   - Current ratio analysis
   - Financial stability metrics

4. **Growth Quality** (0-25 points):
   - Revenue growth consistency
   - Earnings growth quality
   - Sustainable growth indicators

### Usage Example
```bash
python main.py --universe sp500 --strategies enhanced_quality
```

### Default Threshold
- Minimum score: 50/100 for `meets_threshold` flag
- Provides much better differentiation than basic quality screener

## Free Cash Flow Yield Screener

Screens for stocks with attractive free cash flow yields relative to market capitalization.

### Key Metrics

1. **FCF Yield Calculation**:
   ```python
   fcf_yield = (free_cash_flow / market_cap) * 100
   ```

2. **Quality Indicators**:
   - FCF growth trends
   - FCF vs. net income comparison
   - Capital allocation efficiency

### Usage Example
```bash
python main.py --universe sp500 --strategies free_cash_flow_yield
```

## Historic Value Screener

Advanced mean reversion value screening based on historic valuation analysis with multi-factor scoring system.

### Core Methodology

The Historic Value Screener identifies stocks trading below their historical averages while avoiding distressed situations through comprehensive quality filters.

#### Multi-Factor Scoring (0-100 points)

**Component 1: Valuation Discount Analysis (40% weight)**
- **P/E Ratio Discount**: Current P/E vs. 5-year historical average
- **P/B Ratio Discount**: Price-to-book vs. historical book value trends  
- **EV/EBITDA Discount**: Enterprise value analysis vs. historical norms
- **Historic Average Calculation**: Uses 5-year financial data for proxy estimates

**Component 2: Quality Filters (35% weight)**  
- **Profitability Analysis**: ROE trends and profit margin consistency
- **Financial Stability**: Debt ratios and balance sheet strength
- **Growth Quality**: Revenue and earnings sustainability indicators
- **Management Efficiency**: Asset turnover and capital allocation metrics

**Component 3: Market Structure Analysis (25% weight)**
- **Market Capitalization**: Size and liquidity considerations (minimum $1B)
- **Volatility Patterns**: Beta analysis for risk assessment  
- **Trading Characteristics**: Volume patterns and market behavior
- **Technical Support**: Price stability and momentum indicators

### Distress Avoidance Mechanisms

Critical filters to avoid value traps and distressed situations:

1. **Minimum Thresholds**:
   - Market cap ≥ $1 billion (liquidity requirement)
   - Positive profit margins (profitability requirement)
   - Debt-to-equity < 3.0 (leverage limit)

2. **Quality Requirements**:
   - ROE > -10% (basic profitability floor)
   - Positive operating cash flow trends
   - Stable or improving financial metrics

3. **Market Structure Checks**:
   - Beta < 2.5 (volatility limit)
   - Minimum trading volume thresholds
   - Price stability analysis

### Scoring Examples

**High-Quality Value Opportunity (Score: 75/100)**:
- P/E: 8.5 vs. 15.2 historical average (25 points)
- Strong balance sheet and ROE (27 points) 
- Large cap, stable trading (23 points)

**Moderate Value Play (Score: 45/100)**:
- P/B: 0.8 vs. 1.4 historical average (18 points)
- Average financial metrics (15 points)
- Higher volatility, smaller size (12 points)

### Configuration

**Default Settings**:
- Minimum threshold: 25.0/100 (optimized for S&P 500 distribution)
- Historical lookback: 5 years for financial data
- Market cap minimum: $1 billion
- Maximum debt-to-equity: 3.0

**Customizable Parameters**:
```python
# In config.py
MIN_HISTORIC_VALUE_SCORE = 25.0  # Minimum score threshold
```

### Usage Examples

```bash
# Individual historic value screening
python main.py --universe sp500 --strategies historic_value

# Combined with quality screening  
python main.py --universe sp500 --strategies historic_value,quality,fcf_yield --limit 15

# Russell 2000 value opportunities
python main.py --universe russell2000 --strategies historic_value --limit 25
```

### Theoretical Foundation

Based on mean reversion principles and Benjamin Graham's value investing methodology:

1. **Mean Reversion Theory**: Stock prices tend to revert to historical valuation norms over time
2. **Quality Value Investing**: Focus on financially strong companies at temporary discounts
3. **Distress Avoidance**: Systematic filters to avoid permanent value destruction
4. **Multi-Factor Analysis**: Combines valuation, quality, and market structure for robust screening

### Expected Outputs

**Top Historic Value Candidates (October 2025)**:
- FANG: Score 29.5/100 (Energy sector, P/E 10.13, P/B 0.93)
- GM: Score 28.8/100 (Consumer Cyclical, P/E 8.45, P/B 0.94)  
- BK: Score 27.5/100 (Financial Services, P/E 15.98, P/B 1.38)

**Typical Results**: 400-450 stocks from S&P 500 meet basic criteria, with top 15-20 showing strongest historic value opportunities.

## Insider Buying Screener (Pre-Pump Pattern Detection)

Advanced screener detecting pre-pump insider buying patterns with technical consolidation analysis.

### Multi-Component Scoring (0-100 points)

#### Component 1: Insider Activity Analysis (0-40 points)
- **Buy/Sell Ratio** (0-25 points): Percentage of buy vs. sell transactions
- **Net Share Activity** (0-10 points): Positive net buying bonus
- **Insider Diversity** (0-5 points): Multiple insiders buying confidence boost

#### Component 2: Technical Consolidation Analysis (0-35 points)
- **Price Consolidation** (0-20 points): Low volatility base-building periods
- **Volume Patterns** (0-15 points): Unusual volume during insider activity
- **Support Level Adherence**: Price stability above technical support

#### Component 3: Acceleration Analysis (0-25 points)
- **Recent vs. Historical Activity** (0-15 points): 30-day vs. 90-day comparison
- **Volume Surge** (0-10 points): Recent buying volume above averages
- **Activity Concentration**: Multiple transactions in short timeframes

### Enhanced Thresholds
- **Default threshold**: 65.0/100 (selective for pre-pump patterns)
- **Lookback period**: 60 days (configurable)
- **Consolidation threshold**: <15% annualized volatility
- **Acceleration threshold**: 1.5x recent vs. historical activity

### Usage Example
```bash
python main.py --universe sp500 --strategies insider_buying
```

## Combined Screeners

Multiple pre-configured combined screening strategies for different investment approaches.

### Available Combined Strategies

1. **Traditional Value** (`traditional_value`):
   - P/E ratio + Price-to-book + PEG ratio
   - Classic Graham/Buffett value metrics

2. **High Performance** (`high_performance`):
   - Momentum + Quality + Free Cash Flow Yield
   - Research-backed performance indicators

3. **Comprehensive** (`comprehensive`):
   - All available screening strategies combined
   - Maximum coverage analysis

4. **Distressed Value** (`distressed_value`):
   - Specialized distressed situation screening
   - Turnaround + sector correction focus

### Usage Examples
```bash
# Run individual combined strategies
python main.py --universe sp500 --strategies traditional_value
python main.py --universe sp500 --strategies high_performance

# Compare multiple approaches
python main.py --universe sp500 --strategies traditional_value,high_performance
```

## Analyst Sentiment Momentum Screener

Advanced screener analyzing professional analyst sentiment momentum through rating changes, coverage patterns, and consensus trends.

### Multi-Component Scoring (0-100 points)

#### Component 1: Rating Changes Analysis (0-30 points)
- **Grade Momentum** (0-20 points): Analyzes recent upgrades vs. downgrades over 90-day period
- **Rating Hierarchy**: Strong Sell (1) → Sell (2) → Hold/Neutral (3) → Buy (4) → Strong Buy (5)
- **Momentum Calculation**: Weighted recent changes vs. historical baseline
- **Trend Analysis**: Tracks direction and magnitude of rating shifts

#### Component 2: Price Target Analysis (0-25 points)
- **Target Trends** (0-15 points): Price target revision patterns
- **Consensus Strength** (0-10 points): Agreement among analysts on targets
- **Note**: Limited data availability on current API tier

#### Component 3: Estimate Revisions (0-20 points)
- **Earnings Estimate Changes** (0-12 points): Recent estimate revision patterns
- **Revision Momentum** (0-8 points): Frequency and direction of changes
- **Note**: Limited data availability on current API tier

#### Component 4: Consensus Quality (0-15 points)
- **Agreement Level** (0-10 points): Analyst consensus strength
- **Distribution Analysis** (0-5 points): Range and variance of opinions

#### Component 5: Coverage Analysis (0-10 points)
- **Active Coverage** (0-5 points): Number of analysts covering the stock
- **Coverage Quality** (0-5 points): Institutional analyst participation

### Data Sources and Processing

**Primary Data Source**: Financial Modeling Prep analyst endpoints
- **Working Endpoint**: `/grade/{symbol}` (50+ analyst ratings per stock)
- **Limited Endpoints**: Price targets, estimates, consensus (subscription tier dependent)

**Processing Pipeline**:
```python
# Example grade change analysis
def _calculate_rating_momentum_score(grade_data, symbol):
    """Calculate rating momentum from grade changes"""
    grade_hierarchy = {
        'strong sell': 1, 'sell': 2, 'underweight': 2,
        'hold': 3, 'neutral': 3, 'equal weight': 3,
        'buy': 4, 'overweight': 4,
        'strong buy': 5, 'outperform': 4
    }
    
    # Analyze upgrade/downgrade patterns
    upgrades = sum(1 for change in grade_changes if change > 0)
    downgrades = sum(1 for change in grade_changes if change < 0)
    
    # Calculate momentum score
    if total_changes > 0:
        momentum_ratio = (upgrades - downgrades) / total_changes
        return max(0, min(30, 15 + momentum_ratio * 15))
    
    return 0
```

### Configuration and Thresholds

**Default Settings**:
- Minimum threshold: 20.0/100 for basic screening
- High-quality threshold: 50.0/100 for selective screening
- Lookback period: 90 days for rating analysis
- Coverage requirement: Minimum 5 analyst ratings

**Customizable Parameters**:
```python
# In config.py
ANALYST_SENTIMENT_MIN_SCORE = 20.0  # Minimum score threshold
ANALYST_SENTIMENT_LOOKBACK_DAYS = 90  # Analysis period
ANALYST_SENTIMENT_MIN_COVERAGE = 5  # Minimum analyst count
```

### Expected Performance

**API Performance**:
- Processing speed: ~2-3 seconds per stock
- Data richness: 50+ analyst ratings per covered stock
- Coverage: Most large-cap stocks have significant analyst coverage

**Typical Scoring Results**:
- **High-Quality Stocks** (70-100 points): Strong upgrade momentum with broad coverage
- **Moderate Opportunities** (40-70 points): Mixed sentiment with some positive trends
- **Basic Coverage** (20-40 points): Limited analyst activity or neutral sentiment

### Usage Examples

```bash
# Individual analyst sentiment screening
python main.py --universe sp500 --strategies analyst_sentiment_momentum

# Combined with other momentum strategies
python main.py --universe sp500 --strategies analyst_sentiment_momentum,momentum,quality

# High-selectivity screening
python main.py --universe sp500 --strategies analyst_sentiment_momentum --limit 10

# Russell 2000 coverage analysis
python main.py --universe russell2000 --strategies analyst_sentiment_momentum --limit 25
```

### Implementation Notes

**Data Quality Considerations**:
- Grade data is most reliable and comprehensive
- Price target and estimate endpoints may require higher subscription tier
- Graceful degradation when endpoints return empty data
- Robust error handling for inconsistent API responses

**Scoring Validation**:
- Example: AAPL achieved 26.9/100 score with balanced grade changes
- Stocks with no analyst coverage automatically score 0
- Heavy weighting on actual rating changes vs. theoretical consensus

**Technical Implementation**:
- Integrated with Financial Modeling Prep provider
- Uses existing caching and rate limiting infrastructure
- Follows standard BaseScreener architecture
- Generates detailed reasoning for each scored stock

### Theoretical Foundation

Based on institutional investor sentiment theory and analyst herding behavior:
1. **Momentum Theory**: Analyst upgrades often precede price movements
2. **Information Asymmetry**: Professional analysts have access to non-public information
3. **Institutional Validation**: High analyst coverage indicates institutional interest
4. **Sentiment Persistence**: Positive analyst momentum tends to continue short-term

### Integration with Other Screeners

**Complementary Strategies**:
- **With Quality Screeners**: Validates fundamental strength behind analyst optimism
- **With Momentum Screeners**: Confirms technical trends with professional sentiment
- **With Value Screeners**: Identifies undervalued stocks with improving sentiment

**Combined Strategy Examples**:
```bash
# Professional validation of value opportunities
python main.py --universe sp500 --strategies historic_value,analyst_sentiment_momentum

# High-conviction momentum plays
python main.py --universe sp500 --strategies momentum,analyst_sentiment_momentum,enhanced_quality
```

## Future Enhancements

### Analyst Sentiment Momentum Enhancements
1. **Subscription Tier Upgrade**: Enable full price target and estimate analysis
2. **Sentiment Scoring**: Advanced NLP analysis of analyst reports and commentary
3. **Timing Analysis**: Correlation between analyst changes and optimal entry points
4. **Sector Relative Analysis**: Compare analyst sentiment within industry groups

### Momentum Screener Enhancements
1. **Relative Strength Analysis**: Compare to sector and market performance
2. **Volume Confirmation**: Incorporate volume analysis for momentum validation
3. **Trend Quality**: Assess consistency and sustainability of momentum

### Quality Screener Enhancements
1. **Sector-Specific Metrics**: Customize quality factors by industry
2. **ESG Integration**: Incorporate environmental, social, governance factors
3. **Management Quality**: Add management effectiveness metrics

### Enhanced Quality Improvements
1. **Machine Learning Scoring**: Use ML models for quality prediction
2. **Peer Comparison**: Relative quality scoring within sectors
3. **Time Series Analysis**: Quality trend analysis over multiple periods

### Insider Buying Enhancements
1. **Sentiment Analysis**: Analyze insider trading timing and market conditions
2. **Outcome Tracking**: Track historical success rates of detected patterns
3. **Options Activity**: Incorporate unusual options activity correlation

### Technical Analysis Integration
1. **Chart Pattern Recognition**: Automated technical pattern detection
2. **Support/Resistance Levels**: Dynamic support and resistance calculation
3. **Relative Strength Index**: RSI integration across all screeners
