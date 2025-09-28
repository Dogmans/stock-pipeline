# Enhanced Pre-Pump Insider Buying Screener Documentation

## Overview
The enhanced insider buying screener combines insider trading analysis with technical pattern recognition to identify stocks in "pre-pump" phases. It analyzes insider buying acceleration alongside technical consolidation patterns to find stocks where insider confidence aligns with favorable technical setups.

## Multi-Component Scoring Algorithm (0-100 points)

### Component 1: Insider Activity Analysis (0-40 points)
- **Buy/Sell Ratio (0-25 points)**: Percentage of buy vs. sell transactions
- **Net Share Activity (0-10 points)**: Positive net buying gets bonus points
- **Insider Diversity (0-5 points)**: Multiple insiders buying adds confidence

### Component 2: Technical Consolidation Analysis (0-35 points)  
- **Price Consolidation (0-20 points)**: Low volatility periods indicating base building
- **Volume Patterns (0-15 points)**: Unusual volume during insider activity periods
- **Support Level Adherence**: Price stability above technical support levels

### Component 3: Acceleration Analysis (0-25 points)
- **Recent vs. Historical Activity (0-15 points)**: 30-day vs. 90-day activity comparison
- **Volume Surge (0-10 points)**: Recent buying volume above historical averages
- **Activity Concentration**: Multiple transactions in short timeframes

### Enhanced Thresholds:
- **Default threshold**: 65.0/100 (more selective for pre-pump patterns)
- **Lookback period**: 60 days (configurable)
- **Consolidation threshold**: <15% annualized volatility
- **Acceleration threshold**: 1.5x recent vs. historical activity
- **Volume threshold**: 1.2x recent vs. average volume

## Usage Examples

### Command Line
```powershell
# Run insider buying screener only
python main.py --universe sp500 --strategies insider_buying

# Run with custom threshold (optional)
python main.py --universe russell2000 --strategies insider_buying --limit 20

# Combine with other strategies
python main.py --universe all --strategies insider_buying,value,growth
```

### Programmatic Usage
```python
from screeners.insider_buying import screen_for_insider_buying

# Screen with default parameters
results = screen_for_insider_buying(['ORCL', 'META', 'AAPL'])

# Screen with custom parameters
results = screen_for_insider_buying(
    symbols=['ORCL', 'META', 'AAPL'],
    threshold=75.0,
    lookback_days=90
)
```

## Recent Test Results

### Pipeline Test (2025-09-28)
- **Universe**: S&P 500 (503 stocks)
- **Trades analyzed**: 945 insider trades from last 60 days
- **Stocks with insider activity**: 29 stocks
- **Top performers**:
  - ORCL: 90.0/100 (highest score)
  - FOX: 75.3/100
  - VZ: 72.1/100

### Performance Metrics
- **API calls**: ~10 calls to retrieve 945 trades
- **Processing speed**: ~1,657 symbols/second analysis
- **Data freshness**: Last 60 days of insider activity
- **Coverage**: Full S&P 500 universe

## API Integration

### Financial Modeling Prep v4 Endpoints Used:
- `/api/v4/insider-trading?page={page}` - Paginated insider trading data
- Retrieves comprehensive data including:
  - Filing date and transaction date
  - Insider name and relationship
  - Transaction type (Buy/Sell) and price
  - Number of shares and total value
  - Post-transaction ownership

### Rate Limiting:
- Uses cache-aware throttling system
- Respects FMP API rate limits (300 calls/minute)
- Automatically handles pagination for large datasets

## Integration Status
✅ Fully integrated into main pipeline  
✅ Registered in screener system  
✅ Progress bars implemented  
✅ Comprehensive testing completed  
✅ Documentation complete  

## Configuration
The screener can be configured via the main configuration system:
- Threshold adjustments
- Lookback period modifications  
- Role weighting customization
- API timeout settings

## Maintenance Notes
- Monitor API usage to stay within FMP limits
- Consider caching insider trading data for performance
- Review scoring algorithm quarterly for effectiveness
- Update role mappings as needed for new insider types
