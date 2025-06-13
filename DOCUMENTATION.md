# Stock Screening Pipeline Documentation

This document provides a detailed overview of the stock screening pipeline components and their functions.

## Architecture Overview

The stock screening pipeline is built with a modular architecture that separates concerns into specialized components. This makes the codebase easier to maintain, test, and extend with new functionality.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Data Collection│────▶│ Data Processing │────▶│    Screeners    │
│                 │     │                 │     │                 │
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
| `stock_data.py` | Retrieves historical price data and fundamental information for individual stocks. |
| `cache_manager.py` | Implements file-based caching system to reduce redundant API calls, improve performance, and persist data between program runs. |

### Data Processing

| Module | Description |
|--------|-------------|
| `data_processing.py` | Processes raw data by calculating technical indicators, financial ratios, and other metrics needed for screening. Includes functions for standardizing and normalizing data across different stocks. |
| `utils.py` | Provides common utility functions used throughout the pipeline, including logging setup, directory creation, and data helpers. |

### Screening Engine

| Module | Description |
|--------|-------------|
| `screeners.py` | Implements the various screening strategies based on the "15 Tools for Stock Picking" series. Each strategy is a separate function with configurable parameters, and can be run individually or combined. |

### Caching System

The pipeline includes a comprehensive caching system to improve performance and reduce redundant API calls.

| Feature | Description |
|---------|-------------|
| File-based cache | Cache data is stored in JSON files in the `data/cache` directory, with filenames derived from function names and arguments |
| Configurable expiration | Each cache type can have its own expiration time (default: 24 hours), after which data is automatically refreshed |
| Force refresh option | Any cached function can be forced to ignore cache and fetch fresh data by passing `force_refresh=True` |
| Cache management | Command-line options allow viewing cache stats, clearing all cache, or removing old cache files |
| DataFrame serialization | Special JSON serialization/deserialization for pandas DataFrames ensures proper caching of complex data structures |

### Visualization and Output

| Module | Description |
|--------|-------------|
| `visualization.py` | Creates visualizations of screening results, including charts, tables, and interactive dashboards. Generates both static and dynamic visualizations for analysis and presentation. |

### Orchestration

| Module | Description |
|--------|-------------|
| `main.py` | The main entry point that orchestrates the entire pipeline. Handles command line arguments, executes the data collection, processing, screening, and visualization in sequence. |
| `run_pipeline.py` | Provides convenient wrapper functions for common pipeline use cases with preset configurations. |

### Configuration

| Module | Description |
|--------|-------------|
| `config.py` | Contains all configuration settings for the pipeline, including API keys, screening thresholds, market indexes, and general settings. Centralizes all configurable parameters in one place. |

## Key Components in Detail

### Universe Selection (`universe.py`)

The universe module provides functions for defining and retrieving various stock universes:

- `get_sp500_symbols()`: Retrieves current S&P 500 constituents from Wikipedia
- `get_russell2000_symbols()`: Retrieves Russell 2000 constituents (from cache or Finnhub API)
- `get_nasdaq100_symbols()`: Retrieves NASDAQ 100 constituents from Wikipedia
- `get_stock_universe()`: Main function that returns the specified universe based on configuration

### Market Data Collection (`market_data.py`)

This module gathers market-level data to provide context for stock screening:

- `get_market_conditions()`: Retrieves data on major market indices and VIX
- `is_market_in_correction()`: Determines if the market is in correction based on VIX levels
- `get_sector_performances()`: Calculates performance metrics for market sectors to identify trends

### Stock Data Collection (`stock_data.py`)

Functions for retrieving data on individual stocks:

- `get_historical_prices()`: Fetches historical price data for multiple stocks
- `get_fundamental_data()`: Fetches fundamental data like income statements and balance sheets
- `fetch_52_week_lows()`: Identifies stocks near their 52-week lows

### Data Processing (`data_processing.py`)

This module transforms raw data into usable metrics for screening:

- `calculate_technical_indicators()`: Computes technical indicators like RSI, MACD, and Bollinger Bands
- `calculate_financial_ratios()`: Derives financial ratios from fundamental data
- `calculate_price_statistics()`: Computes statistical measures of price performance
- `process_stock_data()`: Main function that processes raw data into a standardized format

### Screening Strategies (`screeners.py`)

Implements various screening strategies based on value investing principles:

- `screen_for_price_to_book()`: Identifies stocks trading near or below book value
- `screen_for_pe_ratio()`: Finds stocks with low P/E ratios
- `screen_for_52_week_lows()`: Locates stocks near 52-week lows
- `screen_for_fallen_ipos()`: Identifies fallen IPOs that may be ready for a rebound
- `screen_for_cash_rich_biotech()`: Finds biotech stocks with high cash reserves relative to market cap
- `screen_for_sector_corrections()`: Identifies sectors that may be in correction or oversold
- `run_all_screeners()`: Runs multiple screening strategies and combines the results

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
