# Stock Pipeline Tests

This directory contains unit tests for the stock screening pipeline modules.

## Test Files (Updated June 2025)

### Core Tests

- `test_screeners.py`: Tests for the new screener architecture where each screener fetches its own data
- `test_providers.py`: Tests for data providers with API-specific methods
- `test_cache.py`: Tests for the file-based caching system functionality
- `test_data_processing.py`: Tests for data processing and financial ratio calculations

### Supporting Tests

- `test_config.py`: Tests for configuration loading and settings
- `test_main.py`: Tests for the main pipeline orchestration and command-line arguments
- `test_market_data.py`: Tests for market data collection and analysis
- `test_stock_data.py`: Tests for stock price and fundamental data collection
- `test_universe.py`: Tests for stock universe selection
- `test_utils.py`: Tests for utility functions like logging and directory setup
- `test_visualization.py`: Tests for data visualization functions

### Removed Tests

The following test files have been removed as part of our June 2025 refactoring:

- `test_run_pipeline.py`: Removed as it was empty after our architecture changes
- `test_simple.py`: Removed as it contained only trivial placeholder tests

## Running Tests

### Run all tests

```powershell
python -m unittest discover -s tests
```

### Run a specific test file

```powershell
python -m unittest tests.test_cache_manager
```

### Run a specific test case

```powershell
python -m unittest tests.test_cache_manager.TestCacheManager.test_clear_cache
```

## Test Coverage

To generate test coverage reports, install coverage.py and run:

```powershell
pip install coverage
coverage run -m unittest discover -s tests
coverage report
```

To generate an HTML report:

```powershell
coverage html
```

This will create an `htmlcov` directory with an interactive HTML report.
