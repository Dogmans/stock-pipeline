# Stock Screening Pipeline Documentation

This document provides a detailed overview of the stock screening pipeline components and their functions.

## Architecture Overview

The stock screening pipeline is built with a modular architecture that separates concerns into specialized components. This makes the codebase easier to maintain, test, and extend with new functionality.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Data Collection│────▶│ Data Processing │────▶│    Screeners    │
│   & Caching     │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │                                               │
        │                                               ▼
┌─────────────────┐                          ┌─────────────────┐
│                 │                          │                 │
│    Main Orchestrator    ◀────────────────▶│  Visualization  │
│                 │                          │                 │
└─────────────────┘                          └─────────────────┘
```

## Component Details

### Data Collection Modules

These modules handle fetching data from various sources and APIs.

| Module | Description |
|--------|-------------|
| `universe.py` | Defines and retrieves stock universes (S&P 500, NASDAQ 100, Russell 2000) which serve as the basis for screening. |
| `market_data.py` | Gathers market-level data including indices, VIX, and sector performance metrics to provide market context. |
| `data_providers/` | Modular data provider architecture for financial data collection with multiple API support (Financial Modeling Prep, YFinance, Alpha Vantage, Finnhub). |
| `cache_config.py` | Implements file-based caching system to reduce redundant API calls, improve performance, and persist data between program runs. |

### Utilities

| Module | Description |
|--------|-------------|
| `utils/` | Package providing common utility functions used throughout the pipeline:
| | - `logger.py`: Logging setup functionality
| | - `filesystem.py`: Directory and file operations 
| | - `rate_limiter.py`: API rate limiting functionality
| | - `shared_persistence.py`: Shared persistence layer for data storage |

### Screening Engine

The screening engine uses a modular architecture with individual screener modules in the `screeners/` package:

| Module | Description |
|--------|-------------|
| `base_screener.py` | Abstract base class defining the interface for all screeners with standardized methods |
| `pe_ratio.py` | P/E ratio screener for classic value stock identification |
| `price_to_book.py` | Price-to-book value screener following Graham's principles |
| `peg_ratio.py` | PEG ratio screener for growth at reasonable price |
| `quality.py` | Basic quality screener (10-point financial strength assessment) |
| `enhanced_quality.py` | Advanced quality screener (0-100 granular scoring system) |
| `free_cash_flow_yield.py` | Free cash flow yield screener using API calculations |
| `historic_value.py` | **NEW**: Historic value screener for mean reversion opportunities |
| `momentum.py` | Momentum screener based on 6M/3M performance analysis |
| `sharpe_ratio.py` | Risk-adjusted return screener using Sharpe ratios |
| `fifty_two_week_lows.py` | Screener for quality stocks near 52-week lows |
| `insider_buying.py` | Pre-pump insider buying pattern detection |
| `fallen_ipos.py` | Post-IPO stabilization opportunity screener |
| `turnaround_candidates.py` | Financial turnaround situation screener |
| `sector_corrections.py` | Sector-wide correction opportunity detection |
| `combined.py` | Combined screening strategies and pre-configured approaches |
| `utils.py` | Utility functions and screener registry management |

### Caching System

The pipeline includes a comprehensive caching system to improve performance and reduce redundant API calls.

| Feature | Description |
|---------|-------------|
| File-based cache | Cache data is stored in JSON files in the `data/cache` directory, with filenames derived from function names and arguments |
| Configurable expiration | Each cache type can have its own expiration time (default: 24 hours), after which data is automatically refreshed |
| Force refresh option | Any cached function can be forced to ignore cache and fetch fresh data by passing `force_refresh=True` |
| Cache management | Command-line options allow viewing cache stats, clearing all cache, or removing old cache files |
| DataFrame serialization | Special JSON serialization/deserialization for pandas DataFrames ensures proper caching of complex data structures |
| CLI integration | The `main.py` script supports cache management arguments for easier control |

Command-line options for cache management:

```
--cache-info         Display cache statistics and exit
--clear-cache        Clear all cache files before running
--force-refresh      Bypass cache and fetch fresh data for all API calls
--clear-old-cache N  Clear cache files older than N hours
```

See `scripts.md` for examples of combining these options with other commands.

### Visualization and Output

| Module | Description |
|--------|-------------|
| `visualization.py` | Creates visualizations of screening results, including charts, tables, and interactive dashboards. Generates both static and dynamic visualizations for analysis and presentation. |

### Orchestration

| Module | Description |
|--------|-------------|
| `main.py` | The main entry point that orchestrates the entire pipeline. Handles command line arguments, executes the data collection, processing, screening, and visualization in sequence. |

### Configuration

| Module | Description |
|--------|-------------|
| `config.py` | Contains all configuration settings for the pipeline, including API keys, screening thresholds, market indexes, and general settings. Centralizes all configurable parameters in one place. |

## Key Components in Detail

### Universe Selection (`universe.py`)

The universe module provides functions for defining and retrieving various stock universes:

- `get_sp500_symbols()`: Retrieves current S&P 500 constituents from Wikipedia
- `get_russell2000_symbols()`: Retrieves Russell 2000 constituents from iShares ETF holdings
- `get_nasdaq100_symbols()`: Retrieves NASDAQ 100 constituents from Wikipedia
- `get_stock_universe()`: Main function that returns the specified universe based on configuration

### Market Data Collection (`market_data.py`)

This module gathers market-level data to provide context for stock screening:

- `get_market_conditions()`: Retrieves data on major market indices and VIX
- `is_market_in_correction()`: Determines if the market is in correction based on VIX levels
- `get_sector_performances()`: Calculates performance metrics for market sectors to identify trends

### Data Providers (`data_providers/` package)

Modular data collection architecture with multiple API provider support:

- `FinancialModelingPrepProvider`: Primary provider with comprehensive financial data (300 calls/minute)
- `YFinanceProvider`: Yahoo Finance integration for price data and market indices
- `AlphaVantageProvider`: Alpha Vantage API for fundamental data and technical indicators
- `FinnhubProvider`: Finnhub API for real-time data and news sentiment

### Screening Strategies (`screeners/` package)

The pipeline implements 11 comprehensive screening strategies using a standardized BaseScreener architecture:

#### Value Investing Screeners
- `PERatioScreener`: Classic P/E ratio screening (threshold: < 10)
- `PriceToBookScreener`: Graham-style book value analysis (threshold: < 1.2)
- `PEGRatioScreener`: Growth at reasonable price screening
- `HistoricValueScreener`: **NEW** - Mean reversion value screening with multi-factor analysis:
  - Valuation discount scoring (40% weight): P/E, P/B, EV/EBITDA vs historical averages
  - Quality filters (35% weight): ROE, profitability, financial stability
  - Market structure analysis (25% weight): Market cap, volatility patterns
  - Distress avoidance mechanisms and minimum thresholds

#### Quality & Fundamental Screeners  
- `QualityScreener`: Basic financial strength (10-point assessment)
- `EnhancedQualityScreener`: Advanced quality analysis (0-100 granular scoring)
- `FCFYieldScreener`: Free cash flow yield analysis using API calculations

#### Technical & Momentum Screeners
- `MomentumScreener`: 6M/3M weighted performance analysis
- `SharpeRatioScreener`: Risk-adjusted return screening
- `FiftyTwoWeekLowsScreener`: Quality stocks near yearly lows

#### Special Situation Screeners
- `InsiderBuyingScreener`: Pre-pump insider activity pattern detection (0-100 scoring)
- `FallenIPOsScreener`: Post-IPO stabilization opportunities
- `TurnaroundCandidatesScreener`: Financial recovery pattern detection
- `SectorCorrectionsScreener`: Sector-wide correction opportunities

#### Combined Strategies (`combined.py`)
- Pre-configured strategy combinations for common investment approaches
- Traditional value, high performance, and comprehensive screening modes

### Visualization (`visualization.py`)

Creates visual representations of the screening results:

- `create_stock_charts()`: Generates price charts for individual stocks
- `create_dashboard()`: Creates an interactive HTML dashboard with all screening results
- `create_market_overview()`: Visualizes market conditions and sector performance

### Main Script (`main.py`)

The orchestrator of the pipeline:

- Parses command line arguments
- Sets up logging and directories
- Retrieves stock universe and market data
- Fetches and processes stock data
- Runs screening strategies
- Creates visualizations and reports
- Outputs summary information

## Pipeline Workflow

1. **Universe Selection**: Choose which stocks to analyze (S&P 500, Russell 2000, etc.)
2. **Market Analysis**: Check overall market conditions and sector performance
3. **Data Collection**: Gather historical price data and fundamental information
4. **Data Processing**: Calculate metrics and indicators needed for screening
5. **Screening**: Apply various screening strategies to identify promising stocks
6. **Visualization**: Create charts and dashboards to visualize the results
7. **Reporting**: Generate summary reports of the findings

## Extension Points

The modular design allows for easy extension of the pipeline:

- Add new data sources by creating new collection functions
- Implement new screening strategies in the `screeners.py` module
- Create new visualization types in the `visualization.py` module
- Add scheduled runs or automation through cron jobs or schedulers

## Performance Considerations

- API rate limits are respected through batch processing and delays
- Data caching is implemented to reduce redundant API calls
- Parallel processing can be implemented for computationally intensive tasks
