# Cache Management Commands

## View Cache Information
To view information about the current cache:
```powershell
python main.py --cache-info
```

## Clear All Cache
To clear the entire cache before running the pipeline:
```powershell
python main.py --clear-cache
```

## Force Refresh Data
To force refresh all data (bypass cache) during pipeline execution:
```powershell
python main.py --force-refresh
```

## Clear Old Cache Files
To clear cache files older than a specific number of hours (e.g., 48 hours):
```powershell
python main.py --clear-old-cache 48
```
