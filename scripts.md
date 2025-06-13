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
