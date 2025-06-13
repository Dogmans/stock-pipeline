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
2. Set up your API keys in the `config.py` file
3. Run the main pipeline: `python main.py`

## Pipeline Components

- Data Collection:
  - `universe.py`: Stock universe selection (S&P 500, NASDAQ 100, Russell 2000)
  - `market_data.py`: Market-level data collection (indices, VIX, sectors)
  - `stock_data.py`: Individual stock data collection (prices, fundamentals)

- Core Processing:
  - `data_processing.py`: Tools to process and clean the collected data
  - `screeners.py`: Implementation of various stock screening strategies
  - `visualization.py`: Functions to visualize screening results

- Orchestration:
  - `main.py`: Main script to run the complete pipeline
  - `run_pipeline.py`: Wrapper script with common execution options
  - `utils.py`: Common utilities and helper functions

## Running the Pipeline

Basic usage:
```
python main.py
```

For common use cases:
```
python run_pipeline.py --quick   # Quick scan of S&P 500
python run_pipeline.py --full    # Comprehensive scan of all stocks
python run_pipeline.py --value   # Value-focused strategies only
```

## Configuration

Edit `config.py` to adjust:
- API keys
- Screening thresholds
- Market indexes to watch
- Stock universes to scan

For detailed documentation on all components, see [DOCUMENTATION.md](DOCUMENTATION.md)
