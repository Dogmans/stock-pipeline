# Stock Screening Pipeline

This pipeline implements a comprehensive stock screening system based on the value investing strategies outlined in the "15 Tools for Stock Picking" series.

## Key Screening Criteria

1. **Book Value Analysis**: Identify stocks trading close to or below book value
2. **P/E Ratio Filtering**: Focus on stocks with low P/E ratios (ideally < 10)
3. **52-Week Low Detection**: Find quality stocks near their 52-week lows, especially during market downturns
4. **IPO Analysis**: Target fallen IPOs that have stabilized and are approaching profitability
5. **Debt & Cash Analysis**: Evaluate debt levels, cash runway, and burn rate
6. **Catalyst Detection**: Identify upcoming catalysts that could drive price movements
7. **Market & Sector Analysis**: Identify sector-specific downturns for targeted investments

## Setup Instructions

### 1. Environment Setup
```bash
# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# or source venv/bin/activate  # Linux/Mac

# Install requirements
pip install -r requirements.txt
```
Note: TA-Lib may require additional setup steps. See [TA-Lib Installation Guide](https://github.com/mrjbq7/ta-lib#installation)

### 2. API Configuration
1. Copy the `.env` template and configure your API keys:
   ```bash
   # Edit .env file with your API keys
   FINANCIAL_MODELING_PREP_API_KEY=your_key_here
   ```

2. **Required API Keys:**
   - **Financial Modeling Prep** (Primary): [Get API Key](https://financialmodelingprep.com/developer/docs) - Paid tier recommended (300 calls/minute)

### 3. VS Code Setup (Optional)
Pre-configured debug configurations are available:
- **Debug SP500 All Strategies**: Run all screeners on S&P 500
- **Debug Russell2000 All Strategies**: Run all screeners on Russell 2000  
- Press `F5` or use Run and Debug panel

### 4. Quick Start
```bash
python main.py --universe sp500 --strategies all --limit 20
```

## Pipeline Components

- Data Collection:
  - `universe.py`: Stock universe selection (S&P 500, Russell 2000, custom lists)
  - `market_data.py`: Market-level data collection (indices, VIX, sectors)
  - `cache_config.py`: Caching system to reduce redundant API calls
  - `data_providers/`: Modular data provider architecture for financial data

- Core Processing:
  - `screeners/`: Package containing modular stock screening strategies
    - `__init__.py`: Package exports
    - `common.py`: Common screening utilities
    - `utils.py`: Helper functions for running screeners
    
    **Value Screening:**
    - `pe_ratio.py`: P/E ratio screener (classic value metric)
    - `price_to_book.py`: Book value screener (Graham-style value)
    - `peg_ratio.py`: PEG ratio screener (growth at reasonable price)
    
    **Technical & Market Timing:**
    - `fifty_two_week_lows.py`: 52-week low detection
    - `momentum.py`: Momentum screener (6M/3M performance analysis)
    - `sharpe_ratio.py`: Risk-adjusted return screener
    
    **Quality & Fundamental:**
    - `quality.py`: Basic quality screener (financial strength)
    - `enhanced_quality.py`: Enhanced quality screener (0-100 granular scoring)
    - `free_cash_flow_yield.py`: Free cash flow yield screener
    - `historic_value.py`: Historic value screener (trading below historical averages)
    
    **Special Situations:**
    - `fallen_ipos.py`: IPO analysis (stabilized post-IPO opportunities)
    - `turnaround_candidates.py`: Turnaround candidate detection
    - `insider_buying.py`: Pre-pump insider buying patterns
    - `sector_corrections.py`: Sector correction detection
    
    **Combined Strategies:**
    - `combined.py`: Multiple combined screening approaches
  - `visualization.py`: Functions to visualize screening results

- Orchestration:
  - `main.py`: Main script to run the complete pipeline
  - `utils/`: Package containing common utilities and helper functions
    - `logger.py`: Logging setup
    - `filesystem.py`: Directory and file operations
    - `rate_limiter.py`: API rate limiting

## Running the Pipeline

The main script for running the pipeline is `main.py`:

### Running the Pipeline with main.py
The core implementation with all available options and fine-grained control:

```
python main.py --universe sp500 --strategies value,growth --limit 100
```

Use main.py directly when you need detailed control over specific parameters or for advanced customizations.

Cache management options:
```
python main.py --cache-info        # Display cache information
python main.py --clear-cache       # Clear all cache before running
python main.py --force-refresh     # Bypass cache and fetch fresh data
python main.py --clear-old-cache 24  # Clear cache older than 24 hours
```

See the `scripts.md` file for additional examples and command combinations.

### Cache Management

The pipeline includes a caching system to reduce redundant API calls:

```bash
python main.py --cache-info        # Show cache statistics
python main.py --clear-cache       # Clear all cache files
python main.py --clear-old-cache 48  # Clear cache files older than 48 hours
python main.py --force-refresh     # Force refresh all data ignoring cache
```

For more options, see:
```bash
python main.py --help
```

## Configuration

Edit `config.py` to adjust:
- API keys
- Screening thresholds
- Market indexes to watch
- Stock universes to scan

For detailed documentation on all components, see [DOCUMENTATION.md](DOCUMENTATION.md)

## Available Screening Strategies

The pipeline includes comprehensive screening strategies across multiple investment approaches:

### Value Investing
- **P/E Ratio Screening**: Classic low P/E ratio detection (< 10 default)
- **Price-to-Book Screening**: Graham-style book value analysis (< 1.2 default)
- **PEG Ratio Screening**: Growth at reasonable price analysis

### Quality & Fundamental Analysis
- **Quality Screening**: Basic financial strength assessment (10-point scale)
- **Enhanced Quality Screening**: Advanced quality analysis (0-100 granular scoring)
  - ROE Analysis (0-25 points)
  - Profitability Analysis (0-25 points) 
  - Financial Strength (0-25 points)
  - Growth Quality (0-25 points)
- **Free Cash Flow Yield**: Uses API's pre-calculated FCF yield for accurate valuation screening
- **Historic Value Screening**: Identifies stocks trading below historical averages (0-100 scoring)
  - Valuation Discount Analysis (40% weight): P/E, P/B, EV/EBITDA vs historical norms
  - Quality Filters (35% weight): ROE, profit margins, financial stability
  - Market Structure Analysis (25% weight): Market cap, volatility, trading patterns
  - Distress Avoidance: Minimum market cap, debt limits, profitability requirements

### Technical & Momentum
- **Momentum Screening**: 6-month/3-month performance analysis
- **Sharpe Ratio Screening**: Risk-adjusted return analysis
- **52-Week Low Detection**: Quality stocks near yearly lows

### Sentiment Analysis
- **Analyst Sentiment Momentum**: Professional analyst sentiment analysis (0-100 scoring)
  - Rating Changes Analysis (30% weight): Upgrade/downgrade momentum over 90 days
  - Price Target Analysis (25% weight): Target revision patterns (limited data availability)
  - Estimate Revisions (20% weight): Earnings estimate trends (limited data availability)
  - Consensus Quality (15% weight): Analyst agreement strength
  - Coverage Analysis (10% weight): Active analyst coverage patterns
  - **Data Source**: Financial Modeling Prep analyst grades (50+ ratings per stock)

### Special Situations
- **Fallen IPO Analysis**: Post-IPO stabilization opportunities
- **Turnaround Candidates**: Financial recovery pattern detection
- **Insider Buying Patterns**: Pre-pump insider activity detection (0-100 scoring)
  - **Requires actual insider purchases** - Stocks with zero insider buying automatically get 0 score
  - Insider Activity Analysis (0-40 points)
  - Technical Consolidation (0-35 points)
  - Acceleration Analysis (0-25 points)
- **Sector Corrections**: Sector-wide downturn opportunities

### Combined Strategies
- **Traditional Value**: P/E + P/B + PEG combined
- **High Performance**: Momentum + Quality + FCF Yield
- **Comprehensive**: All strategies combined
- **Distressed Value**: Specialized distressed situation analysis

### Usage Examples
```bash
# Quick start - all strategies on SP500 (limited results)
python main.py --universe sp500 --strategies all --limit 20

# Individual screeners
python main.py --universe sp500 --strategies pe_ratio
python main.py --universe sp500 --strategies enhanced_quality  
python main.py --universe russell2000 --strategies insider_buying
python main.py --universe sp500 --strategies historic_value

# Combined strategies (pre-configured)
python main.py --universe sp500 --strategies traditional_value
python main.py --universe sp500 --strategies high_performance
python main.py --universe sp500 --strategies comprehensive

# Custom combinations
python main.py --universe russell2000 --strategies momentum,enhanced_quality,insider_buying
python main.py --universe sp500 --strategies peg_ratio,fcf_yield,quality --limit 30
python main.py --universe sp500 --strategies historic_value,quality,fcf_yield --limit 15

# Cache management
python main.py --cache-info                    # Show cache statistics  
python main.py --clear-cache                   # Clear all cache
python main.py --force-refresh --limit 10      # Fresh data (testing)
```

## Performance & Rate Limiting

- **Financial Modeling Prep**: 300 calls/minute (paid tier recommended)
- **Caching System**: 24-hour data expiry reduces API usage
- **Intelligent Throttling**: Cache-aware rate limiting
- **Progress Tracking**: Real-time progress bars for long operations

## Recent Updates

### October 2025 - Historic Value Screener & Major Improvements  
- **NEW: Historic Value Screener**: Comprehensive value screening based on mean reversion theory
  - Multi-factor scoring: Valuation discount (40%), Quality (35%), Market structure (25%)
  - Historic P/E, P/B, EV/EBITDA analysis using 5-year financial data
  - Quality filters to avoid distressed situations (debt ratios, profitability, market cap)
  - Distress avoidance mechanisms with minimum thresholds
- **Fixed All Screener Issues**: Resolved sector display, field mapping, and method signature problems
  - Quality screener: Fixed field name mismatches (DebtToEquityRatio vs DebtToEquity)
  - FCF Yield screener: Improved API integration and calculation logic  
  - Enhanced Quality screener: Standardized BaseScreener method signatures
  - Momentum/Sharpe screeners: Fixed sector information display issues
- **Enhanced Data Processing**: Improved data structure flattening for BaseScreener compatibility
- **Updated Configuration**: Added historic value threshold settings (MIN_HISTORIC_VALUE_SCORE)
- **Comprehensive Testing**: All 11 screeners now working correctly with proper stock discovery

### September 2025 - Documentation & Screener Updates  
- **Updated Documentation**: Comprehensive README and screener method documentation
- **Enhanced Quality Screener**: 0-100 granular scoring system for better differentiation
- **Insider Buying Screener**: Advanced pre-pump pattern detection with technical analysis
- **Rate Limiting**: Properly configured for Financial Modeling Prep (300 calls/minute)

### June 2025 - Architecture Improvements
- Updated data provider architecture to allow API-specific method naming
- Removed redundant test files and improved test organization
- Enhanced documentation for the new architecture

## Key Features

1. **Comprehensive Screening**: 15+ screening strategies across value, quality, momentum, and special situations
2. **Advanced Scoring**: Granular 0-100 point systems for quality and insider buying analysis
3. **API Integration**: Optimized for Financial Modeling Prep with proper rate limiting (300 calls/minute)
4. **Caching System**: Intelligent caching reduces API usage and improves performance
5. **VS Code Integration**: Pre-configured debug setups for efficient development and testing
6. **Flexible Output**: Detailed reports with proper metric formatting and threshold indicators

## Modules

- `main.py` - Main entry point and orchestrator
- `run_pipeline.py` - Command-line wrapper with common presets
- `universe.py` - Stock universe selection
- `market_data.py` - Market condition assessment
- `data_providers/` - Modular data provider architecture
- `screeners/` - Individual screening strategy modules
- `visualization.py` - Reporting and visualization
- `cache_config.py` - API response caching system
