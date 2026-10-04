# Scripts

Run scripts from the repository root with the installed project interpreter.

| Script | Purpose |
| --- | --- |
| `start_visual_editor.ps1` | Checks the `.venv-ui` interpreter/build, starts the local editor on port 8765 |
| `run_offline_regressions.py` | Temporary storage and network-blocked regressions, including TAM |
| `diagnose_fmp_performance.py` | Explicit `--live` FMP timing probe; optional connection comparison |
| `test_company_overview.py` | Manual provider inspection; may use live data |
| `run_country_test.py` | Manual country-universe/provider checks |
| `python/test_turnaround_screener.py`, `powershell/test_turnaround_screener.ps1` | Legacy turnaround diagnostics; inspect assumptions before use |
| `powershell/manage_docs.ps1` | Documentation maintenance helper |

`web/scripts/capture-readme.mjs` is a separate frontend screenshot helper run from `web/`; it supplies labelled demo data rather than live market results.

[Installation](../README.md), [testing](../docs/testing.md), [PowerShell commands](../docs/powershell_commands.md), [cache commands](powershell/cache_management.md).
