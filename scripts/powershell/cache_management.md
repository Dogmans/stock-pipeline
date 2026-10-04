# Cache commands

```powershell
.venv-ui\Scripts\python.exe main.py --cache-info
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies quality --clear-cache
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies quality --force-refresh
```

`--clear-cache` and `--force-refresh` clear the global disk cache before a normal CLI run. Workflow CLI dispatch occurs earlier and does not process these flags. Editor score snapshots are a separate cache.

`--clear-old-cache N` does not selectively delete entries: below 168 hours it does nothing; at least 168 hours clears all entries. Prefer documented exact-key invalidation for targeted operations. [Full cache semantics](../../docs/cache_usage.md).
