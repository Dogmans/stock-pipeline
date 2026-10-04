# Reports and audit exports

The default CLI writes text reports through `reporting.py`; it does not automatically generate charts or the legacy HTML dashboard.

```powershell
.venv-ui\Scripts\python.exe main.py --universe sp500 --strategies pe_ratio,quality --limit 20
Get-Content output\screening_report_sp500.md
```

Normal runs write `screening_report_<universe>.md` and `summary_<universe>.txt`. Country suffixes use the country key, such as `screening_report_japan.md`. Results are filtered by `meets_threshold` when present; legacy rows without that flag are treated as already selected. Failed stocks are not used to pad a short report. `--limit 0` displays all passing rows; positive limits affect display, not universe processing.

Workflow CLI runs write `workflow_results.json`, `workflow_report.md`, and `workflow_summary.txt`. Reports contain records routed into output nodes, which may deliberately include Fail/Unavailable branches; the JSON retains their actual per-node outcomes.

TAM additionally exports `proven_technology_emerging_tam_summary.json`, `_candidates.json`, `_near_misses.json`, and `_audit.json`. Normal CLI exports live in the output directory; workflow CLI exports live in its per-node subdirectory. Editor downloads use `tam_<kind>.json`. Candidate/near-miss caps do not alter hard-filter outcomes or remove rows from the full audit. [TAM methodology](proven_technology_emerging_tam.md).

Editor CSV exports the selected outcome's matching rows, including nested evidence serialized as JSON. Stock tables display at most 500 matching rows, while CSV includes all matching rows. Saved editor runs retain their workflow and results locally.
