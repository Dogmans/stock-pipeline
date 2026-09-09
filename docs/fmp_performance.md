# FMP performance investigation — 2026-09-09

## Finding

Measured delays predominantly came from HTTP round trips, including connection
setup, rather than throttling. Reusing a connection reduced repeated quote request
time from approximately 363 ms to 95 ms in this small sample. This is not a
full-pipeline speedup estimate or a measurement of FMP server processing alone.

The initial investigation did not change production behavior. The follow-up below
implements the requested fixes.

## Implemented follow-up

FMP now shares a `requests.Session` across provider instances, including insider
trading requests, and closes it at process exit. The session is kept at module level
so mutable transport state does not enter the serialized provider cache keys.
Existing rate limits remain in place.

The manual cache checker now resolves each decorated method's DiskCache
`__cache_key__` and checks membership using the original arguments. All seven FMP
decorated methods use it. Membership correctly handles empty/None results and
expired entries. The outer memoization decorator remains unchanged.

Four additional offline regressions cover all seven probes, argument/credential
separation, stable caching across provider instances after HTTP use, and shared
transport for both central and insider requests. All 14 offline tests pass.

A nine-request live AAPL check after the change returned HTTP 200 throughout:

- Total HTTP time fell from 3.62 seconds in the original nine-request probe to
  1.325 seconds in this check (about 63% lower; small samples, not a full-run forecast).
- Cold overview took 0.826 seconds; cold history took 0.118 seconds.
- Established-session quote took 96 ms; analyst/price-target requests took about 100 ms.
- Repeated overview/history remained sub-millisecond, including with a new instance.
- Both the actual memoized-key check and manual cache probe reported a hit.
- No throttle waits occurred in this small check.

Raw timing metadata is in `output/fmp_performance_after.json`. Analyst endpoint
caching and throttle consolidation remain follow-up work.

## Evidence before the fix

Two small live AAPL probes made 24 requests in total, all returning HTTP 200.
The diagnostic used a separate temporary cache and captured HTTP durations and
actual sleep durations without recording API keys or response bodies.

| Operation | Observed time | HTTP requests on repeat |
|---|---:|---:|
| Cold company overview, four endpoints | 1.70–1.96 seconds | 0 |
| Cold one-year price history | 0.47 seconds | 0 |
| Cached overview/history | Under 1 ms | 0 |
| Analyst consensus | About 365 ms | 1 |
| Price target consensus | About 365 ms | 1 |
| Quote with a fresh connection | 363 ms median across three requests | 1 |
| Quote over an established session | 95 ms across two warm requests | 1 |

Both probes recorded zero throttle sleep. A new provider instance reused cached
overview/history results successfully. Connection reuse was measured by temporarily
replacing the diagnostic's HTTP transport with `requests.Session.get`; the first
request still took 377 ms, while the next two took 95 ms each. The limiter remained
active during these requests.

The existing log spans July 4 through September 9. It contains 93,134 throttler
method-call messages but only 20 explicit sleep entries, totaling approximately four
seconds at the log's precision, and no logged minute-limit waits. Approximate
serial connection-start/response matching gives historical medians of 327–332 ms
for quote/profile/analyst consensus, 413 ms for key metrics and ratios, and 426 ms
for price history. These are log-derived estimates, not instrumented timings.
One HTTP 429 response appears in the parsed HTTP response logs; absence of local
waits therefore does not prove the remote account limit was never exceeded.

## Throttling and caching observations before the fix

- `utils/rate_limiter.py` applies the configured 300 calls/minute limit at the
  central FMP request boundary; insider trading also invokes it explicitly.
- `utils/throttling.py` adds a 5 calls/second, 300 calls/minute layer around selected
  provider methods. It counts method entries, not individual HTTP requests. An
  overview fetch may make four requests, and analyst methods lack that decorator.
  Consequently this layer does not enforce a universal five HTTP requests/second.
- A controlled-clock check of the method throttler, configured to three calls per
  minute and five per second, produced waits of 0.2, 0.2, and 59.6 seconds for four
  immediate calls. Its sequential timing behavior worked in this check.
- The manual cache probe constructs string keys that do not match DiskCache's
  memoization keys. The diagnostic confirmed the real key existed while the manual
  probe missed. Ordinary cache hits still bypass throttling because the actual
  memoization decorator is outside the throttling decorator.
- Analyst consensus and price-target methods lack memoization. Repeat calls made
  fresh requests, including calls shared between analyst and composite screeners.
- The current transport uses standalone `requests.get` calls, so successive calls
  do not retain the connection through a shared session.

## Recommended order

1. **Completed:** reuse a session for FMP requests and close it at process exit.
2. Cache analyst/price-target results with suitable expiry and refresh semantics.
3. Consolidate throttling at the HTTP request boundary before introducing concurrency
   or relying on a five-request/second limit. Keep the configured account limit.
4. Add safe per-endpoint timing and explicit request timeouts. The diagnostic imposed
   a five-second connect and fifteen-second read timeout; production's central helper
   currently supplies neither.

## Reproduce

With the project dependencies installed, run from the repository root:

```powershell
python scripts/diagnose_fmp_performance.py --live --compare-session --output output/fmp_performance_diagnostic.json
```

`--live` explicitly enables a small set of authenticated, read-only FMP requests.
The existing `.env` supplies the key. Without `--compare-session`, the diagnostic
omits the six quote comparison requests. The output file contains timing metadata
and status codes only. Current sample results are stored in the ignored `output/`
directory; this document preserves the findings.
