# Testing

Run commands from the repository root using the installed project environment. The normal regression runner isolates temporary cache/output storage and blocks external network access.

```powershell
.venv-ui\Scripts\python.exe scripts/run_offline_regressions.py
```

It currently includes reporting/scoring regressions, FMP transport/cache checks, workflow validation/routing, the visual API and TAM. TAM coverage includes strict/inclusive boundaries, financial survivability, penalties without exclusion, missing data, annual/TTM fallback, currency mismatch, staging, benchmark counts and export limits.

Research and price-change tests can be run separately:

```powershell
.venv-ui\Scripts\python.exe -m unittest tests.test_research tests.test_price_change tests.test_return_on_equity
```

The repository also contains older integration and legacy-function tests. Full discovery is not the default offline check: some tests make live API calls, need credentials, clear shared cache, or contain assertions/imports from earlier implementations.

```powershell
# Includes legacy and potentially live integration tests
.venv-ui\Scripts\python.exe -m unittest discover -s tests
```

## Frontend and browser checks

```powershell
cd web
npm test
npm run build
npx playwright install chromium
npx playwright test
```

Frontend unit tests cover graph mechanics, rule descriptions, rankings, near misses and evidence exports. Browser tests stub API data and run desktop/mobile projects. Set `$env:STOCK_UI_BROWSER_CHANNEL='msedge'` to use installed Edge. `STOCK_UI_EXTERNAL_SERVER` and `STOCK_UI_BASE_URL` can target an existing local build. [Research test details](stock-research.md).

If Vite's bundled config loader cannot write its temporary config file, use `npm run build -- --configLoader runner`. A write-denied output directory is a separate filesystem issue; the alternate loader does not bypass it.

## Fixture and cache rules

Mock data at the actual provider import/use location. Use normalized field names and the correct units/statement dates. Do not patch historical package exports that no longer exist. For isolated cache tests, use temporary storage or exact memoization keys and cleanup. Avoid broad production-cache clearing for routine unit tests. [Cache guide](cache_usage.md).

If coverage.py is separately installed, run coverage with the same interpreter, for example `python -m coverage run scripts/run_offline_regressions.py`, then `python -m coverage report`. Coverage is not part of the pinned requirements.

[Tests directory](../tests/README.md), [legacy turnaround tests](testing/turnaround_screener_testing.md). Passing mocked tests does not verify live FMP entitlements or broad-universe survivor counts.
