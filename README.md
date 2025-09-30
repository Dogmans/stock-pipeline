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

1. Install requirements: `pip install -r requirements.txt`
   - Note: TA-Lib may require additional setup steps. See [TA-Lib Installation Guide](https://github.com/mrjbq7/ta-lib#installation)
2. Set up your API keys in the `config.py` file
3. Run the main pipeline: `python main.py`

## Pipeline Components

- Data Collection:
  - `universe.py`: Stock universe selection (S&P 500, Russell 2000, custom lists)
  - `market_data.py`: Market-level data collection (indices, VIX, sectors)
  - `stock_data.py`: Individual stock data collection (prices, fundamentals)
  - `cache_config.py`: Caching system to reduce redundant API calls

- Core Processing:
  - `data_processing.py`: Tools to process and clean the collected data, calculate indicators and financial ratios
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
- **Free Cash Flow Yield**: FCF-based valuation screening

### Technical & Momentum
- **Momentum Screening**: 6-month/3-month performance analysis
- **Sharpe Ratio Screening**: Risk-adjusted return analysis
- **52-Week Low Detection**: Quality stocks near yearly lows

### Special Situations
- **Fallen IPO Analysis**: Post-IPO stabilization opportunities
- **Turnaround Candidates**: Financial recovery pattern detection
- **Insider Buying Patterns**: Pre-pump insider activity detection (0-100 scoring)
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
# Run individual screeners
python main.py --universe sp500 --strategies pe_ratio
python main.py --universe sp500 --strategies enhanced_quality
python main.py --universe sp500 --strategies insider_buying

# Run combined strategies
python main.py --universe sp500 --strategies traditional_value
python main.py --universe sp500 --strategies high_performance

# Mix and match
python main.py --universe sp500 --strategies momentum,quality,insider_buying
```

## Recent Updates

### June 2025
- Updated data provider architecture to allow API-specific method naming
- Removed redundant test files and improved test organization
- Enhanced documentation for the new architecture

### November 2023
- Refactored the screeners to fetch their own data directly from providers
- Removed chunked processing
- Simplified the overall codebase

## Recent Enhancements

1. **Enhanced Screener Behavior** (June 2025):
   - All screeners now return complete stock sets ranked by relevant metrics
   - Each result includes a `meets_threshold` flag to filter for traditional threshold-based screening
   - Results can be used individually or by the combined screener for comprehensive scoring
   - See `docs/screener_methods/enhanced_behavior.md` for details

2. **Combined Screener** (June 2025):
   - New screener that ranks stocks based on their performance across multiple strategies
   - Calculates average position across different metrics (P/E, P/B, PEG, etc.)
   - Gives slight bonus to stocks appearing in multiple screeners
   - See `docs/screener_methods/combined.md` for details

3. **PEG Ratio Screener** (June 2025):
   - Calculates Price/Earnings to Growth ratio to find stocks undervalued relative to growth
   - Uses either latest quarterly data or annual growth rates as available
   - See `docs/screener_methods/peg_ratio.md` for details

## Modules

- `main.py` - Main entry point and orchestrator
- `run_pipeline.py` - Command-line wrapper with common presets
- `universe.py` - Stock universe selection
- `market_data.py` - Market condition assessment
- `stock_data.py` - Stock data collection
- `data_processing.py` - Data processing and calculation
- `screeners.py` - Screening strategies
- `visualization.py` - Reporting and visualization
- `cache_manager.py` - API response caching system
