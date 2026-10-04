# PowerShell commands

Run from the repository root after following [installation](../README.md). Examples explicitly use the editor environment so an unrelated system Python does not run without dependencies.

## Editor and build

```powershell
.\scripts\start_visual_editor.ps1
# Or start the API directly:
.venv-ui\Scripts\python.exe visual_api.py
```

In a separate terminal for frontend development:

```powershell
cd web
npm run dev
```

Build served assets from `web/` with `npm run build`. If the default config-loader temporary file cannot be written, `npm run build -- --configLoader runner` avoids that loader path. Restart the Python server for backend changes; reload the browser for a new frontend build.

## Screens and workflows

```powershell
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies pe_ratio,quality --limit 20
.venv-ui\Scripts\python.exe main.py --symbols HIMX,LTRX,PNG.V --strategies proven_technology_emerging_tam
.venv-ui\Scripts\python.exe main.py --workflow workflows/proven_technology_emerging_tam.json --output output/tam
.venv-ui\Scripts\python.exe main.py --universe country:japan --strategies quality
.venv-ui\Scripts\python.exe main.py --help
```

`--limit 0` displays all selected/passing results. It never limits API processing. Country universes are ETF holdings and `all` is an index union. The TAM discovery universe is `fmp_listed`; its exchange scope is documented in [the TAM guide](guides/proven_technology_emerging_tam.md).

Only [registered strategy IDs](screener_methods.md) work in the current CLI. Historical `value`, `growth`, `combined`, `--full` and `--chunk-size` examples are not supported commands. Rate/statistics flags listed by the parser are currently inactive; see [providers](../data_providers/README.md).

## Cache

```powershell
.venv-ui\Scripts\python.exe main.py --cache-info
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies quality --force-refresh
```

Refresh flags apply to normal CLI dispatch, not the earlier workflow path. Age clearing is coarse; see [cache semantics](cache_usage.md).

## Validation and diagnostics

```powershell
.venv-ui\Scripts\python.exe scripts/run_offline_regressions.py
.venv-ui\Scripts\python.exe -m unittest tests.test_research tests.test_price_change tests.test_return_on_equity
.venv-ui\Scripts\python.exe scripts/diagnose_fmp_performance.py --live --compare-session --output output/fmp_performance_diagnostic.json
```

The diagnostic's `--live` explicitly makes authenticated read-only requests. Normal offline checks do not. Browser setup and environment-variable examples are in [testing](testing.md). Editor and workflow logic is configured in saved JSON; IDE tasks are convenience files, not the authoritative command reference.
