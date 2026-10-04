# PowerShell test commands

Run from the repository root:

```powershell
.venv-ui\Scripts\python.exe scripts/run_offline_regressions.py
.venv-ui\Scripts\python.exe -m unittest tests.test_research tests.test_price_change tests.test_return_on_equity
```

Frontend checks run from `web/`:

```powershell
npm test
npm run build
npx playwright test
```

Full unittest discovery includes potentially live integrations and older assertions. There is no root `run_tests.ps1` or `tests.test_cache_manager` module in the current repository. See [the testing guide](../../docs/testing.md) for browser setup, coverage and isolation.
