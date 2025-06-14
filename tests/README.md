# Stock Pipeline Tests

This directory contains unit tests for the stock screening pipeline modules.

## Test Files

- `test_cache_manager.py`: Tests for the file-based caching system functionality
- `test_config.py`: Tests for configuration loading and settings
- `test_data_processing.py`: Tests for data processing and financial ratio calculations
- `test_main.py`: Tests for the main pipeline orchestration and command-line arguments
- `test_market_data.py`: Tests for market data collection and analysis
- `test_run_pipeline.py`: Tests for the pipeline runner script and command-line options
- `test_screeners.py`: Tests for stock screening strategies
- `test_stock_data.py`: Tests for stock price and fundamental data collection
- `test_universe.py`: Tests for stock universe selection
- `test_utils.py`: Tests for utility functions like logging and directory setup
- `test_visualization.py`: Tests for data visualization functions

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
