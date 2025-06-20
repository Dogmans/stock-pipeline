# Testing Commands

This guide documents the various ways to run tests for the stock pipeline project.

## Basic Test Commands

### Run All Tests
To run all unit tests for the pipeline:
```powershell
python -m unittest discover -s tests
```

### Run Tests for a Specific Module
To run tests for a specific module (e.g., cache_manager):
```powershell
python -m unittest tests.test_cache_manager
```

### Generate Test Coverage Report
To generate a test coverage report:
```powershell
# Run tests with coverage
coverage run -m unittest discover -s tests

# Display coverage report
coverage report

# Generate HTML coverage report
coverage html
```

## Using PowerShell Test Scripts

### Using the PowerShell Test Script
To run tests using the PowerShell script:
```powershell
.\run_tests.ps1
```

To run tests for a specific module:
```powershell
.\run_tests.ps1 test_cache_manager
```

To run tests with coverage:
```powershell
.\run_tests.ps1 -Coverage
```

## VS Code Tasks

Remember that you can run the predefined VS Code tasks for testing:

- Run All Tests
- Run All Tests with Coverage
- Run Test Module
- Run Pipeline with Sequential Tests
- Generate HTML Coverage Report
