# Cache and refresh semantics

The application uses DiskCache `FanoutCache` with eight shards under `data/cache`. It stores serialized Python objects, including DataFrames; it is not a directory of hand-written JSON response files. Expiry is set per memoized method, in seconds.

## Cache layers

- FMP disk responses persist across processes. Existing statements normally expire after 168h; overview and legacy price histories after 24h; stock news after 30min. Discovery successes expire after 24h.
- Raw stable research statements, including quarterly inputs shared by the stock profitability panel and four profitability screens, expire after 24h. They use `get_research_statements()`, separately from the 168h legacy statement methods. Profitability calculations have no additional disk cache.
- Workflow score snapshots are in memory: five snapshots, up to 100,000 non-error symbol evaluations each. Restarting the API clears them. Parameter changes create distinct score keys, including profitability `min_percent` edits; explicit score-criterion edits can reuse scores. A new score snapshot or page reload still respects the statement cache.
- Completed editor runs persist separately in `output/workflow_history`. Restoring a run does not refresh its evidence or reuse an in-memory score snapshot automatically.

Stable daily prices share one cache per symbol and account, retained for 30 days. Covered subranges are sliced locally; extensions fill any intervening gap and overlap 14 calendar days. The recent tail refreshes daily (15 minutes for current-day or empty tails); the full retained history reconciles weekly or when overlapping historical closes change. Current-day prices remain provisional. Requests are chunked below FMP's row limit, and failures leave the stored snapshot untouched. Thread locks protect each read/fetch/merge/write sequence within the single API process. Legacy price methods and financial-statement caching are unchanged.

## Correct key-based invalidation

```python
from cache_config import cache, get_cache_info
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
provider = FinancialModelingPrepProvider()
method = provider.get_income_statement
key = method.__cache_key__(provider, 'AAPL', annual=True)
cache.delete(key)
print(get_cache_info())
```

The key must match the original instance and exact positional/keyword argument form. `cache.delete(function, symbol)` is not a supported function-call invalidation pattern. The compatibility `delete_memoized` shim currently clears the entire cache rather than selecting one method.

To wrap a new operation, use `@cache.memoize(expire=24 * 3600)`. Raise on transient errors when they must not be cached; returning an empty object can memoize that failure. The existing FMP price-change history and discovery fetch methods use this exception pattern. Not all older methods do.

## CLI commands

```powershell
.venv-ui\Scripts\python.exe main.py --cache-info
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies quality --force-refresh
```

For normal CLI runs, `--clear-cache` and `--force-refresh` clear the global disk cache before execution. They do not clear editor score snapshots. Workflow dispatch occurs before these options are processed; do not assume `--workflow ... --force-refresh` refreshes data.

`--clear-old-cache N` is a compatibility placeholder: N below 168 hours does nothing; N at least 168 clears the entire cache. It does not delete entries selectively by age. `get_cache_info()` returns `count`, `hits`, `misses`, `size_kb`, `directory`, and `status` when successful. Cache-clearing log counts are approximate.
