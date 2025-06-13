# Stock Pipeline Scripts Documentation

This document contains information about how to run various tasks for the stock pipeline in PowerShell.

## Cache Management Commands

### View Cache Information
To view information about the current cache:
```powershell
python main.py --cache-info
```

### Clear All Cache
To clear the entire cache before running the pipeline:
```powershell
python main.py --clear-cache
```

### Force Refresh Data
To force refresh all data (bypass cache) during pipeline execution:
```powershell
python main.py --force-refresh
```

### Clear Old Cache Files
To clear cache files older than a specific number of hours (e.g., 48 hours):
```powershell
python main.py --clear-old-cache 48
```

## Running the Pipeline

### Quick Scan with Fresh Data
To run a quick scan with fresh data (bypassing cache):
```powershell
python run_pipeline.py --quick --force-refresh
```

### Full Comprehensive Scan with Cache Cleared
To run a full scan after clearing the cache:
```powershell
python run_pipeline.py --full --clear-cache
```

### Value-Focused Scan with Custom Output Directory
To run a value-focused scan with results in a custom directory:
```powershell
python run_pipeline.py --value --output ./value_results
```

## Combined Commands

### Clear Old Cache and Run Full Scan
To clear cache files older than 72 hours and run a full scan:
```powershell
python run_pipeline.py --full --clear-old-cache 72
```

### Cache Information Check Before Running
First check cache info, then run the pipeline if needed:
```powershell
python main.py --cache-info
python run_pipeline.py --quick
```

## Maintenance Tasks

### Removed Deprecated Files
On June 13, 2025, the following unused files were removed from the codebase:

```powershell
del "c:\Programs\stock_pipeline\data_collection.py"
del "c:\Programs\stock_pipeline\data_collection.py.new"
```

These files were no longer used as their functionality had been refactored into more focused modules.

## Maintenance Logs

### 2025-06-13: Codebase Cleanup and Documentation Update

1. Removed unused files:
```powershell
del "c:\Programs\stock_pipeline\data_collection.py"
del "c:\Programs\stock_pipeline\data_collection.py.new"
```

2. Added missing functions to data_processing.py:
   - process_stock_data - Main data processing function 
   - calculate_financial_ratios - Financial ratio calculation function

3. Updated documentation for consistency:
   - Updated README.md with cache management options
   - Updated DOCUMENTATION.md with accurate module descriptions
   - Updated function docstrings in multiple files
   - Added TA-Lib to requirements.txt

4. Cache system fixes:
   - Added proper DataFrame serialization/deserialization
   - Updated all modules to support force_refresh parameter
   - Added CLI options for cache management

5. Added TA-Lib fallback mechanism:
   - Pipeline now works even without TA-Lib installed
   - Provides simplified technical indicator calculations when TA-Lib is unavailable
   - Added installation instructions for TA-Lib

## Package Installation Notes

### Installing TA-Lib

TA-Lib is a technical analysis library that provides advanced technical indicators. Installation can be more complex than standard Python packages because it requires C/C++ compilation.

#### Windows Installation

1. Download the appropriate wheel file from the unofficial builds: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
2. Install the downloaded wheel file:
```powershell
pip install TA_Lib‑0.4.28‑cp310‑cp310‑win_amd64.whl
```
(Replace the filename with the appropriate version for your Python installation)

#### Alternative: Using without TA-Lib

If you can't install TA-Lib, the pipeline will still work but will use simplified indicator calculations:
```powershell
python main.py --value
```
A warning will be displayed, but all functionality will still work with basic indicator calculations.
