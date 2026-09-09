# Stock Pipeline Tests

This directory contains unit tests for the stock screening pipeline modules.

## Test files

### Core Tests

- `test_screeners.py`: Tests for the new screener architecture where each screener fetches its own data
- `test_providers.py`: Tests for data providers with API-specific methods
- `test_cache.py`: Tests for the file-based caching system functionality
- `test_fmp_transport.py`: Tests shared FMP connections and cache-aware throttling
- `test_regressions.py`: Offline regression coverage for scoring and reports
- `test_workflow.py`: Tests workflow validation, branching, caching, and progress
- `test_visual_api.py`: Tests the local workflow API

### Supporting Tests

- `test_config.py`: Tests for configuration loading and settings
- `test_main.py`: Tests for the main pipeline orchestration and command-line arguments
- `test_market_data.py`: Tests for market data collection and analysis
- `test_universe.py`: Tests for stock universe selection
- `test_utils.py`: Tests for utility functions like logging and directory setup
- `test_visualization.py`: Tests for data visualization functions

## Running Tests

### Run the offline regression suite

```powershell
.venv-ui\Scripts\python.exe scripts\run_offline_regressions.py
```

This is the normal project check. It blocks external network access and exercises
the pipeline, FMP transport, workflow engine, and visual API.

### Run all tests, including live API tests

```powershell
python -m unittest discover -s tests
```

Some legacy integration tests require configured API credentials and network access.

### Run a specific test file

```powershell
python -m unittest tests.test_workflow
```

### Run a specific test case

```powershell
python -m unittest tests.test_workflow.WorkflowTests.test_overall_progress_is_monotonic_and_completes
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
