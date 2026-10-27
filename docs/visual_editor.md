# Visual workflow editor

The local editor provides a drag-and-drop view over the existing Python screeners.
The existing CLI remains available. Both interfaces use `workflow.py`, the screener
registry, FMP, and the existing disk cache.

## Install and start

Python 3.12 is recommended. From the repository root:

```powershell
py -3.12 -m venv .venv-ui
.venv-ui\Scripts\python.exe -m pip install -r requirements.txt
.venv-ui\Scripts\python.exe -m pip install -r requirements-ui.txt
cd web
npm ci
npm run build
cd ..
.venv-ui\Scripts\python.exe visual_api.py
```

Open <http://127.0.0.1:8765>. The server binds to localhost and runs one workflow
at a time so FMP rate limiting, connection pooling, and snapshots remain coherent.
API documentation is at <http://127.0.0.1:8765/docs>.

After the first build, start it from the repository root with:

```powershell
.\scripts\start_visual_editor.ps1
```

During frontend development, run `npm run dev` in `web/`; it proxies `/api` to the
Python server. Production assets are generated under ignored `web/dist/`.

## Build and read a workflow

- Drag or click screeners in the library to add them.
- Connect the universe to a screen, then connect Pass, Fail, Unavailable, or Error
  to another screen or shortlist.
- An outcome has one outgoing connection and a node has one input. This keeps
  branches disjoint and Sankey-style counts truthful. Cycles and merges are rejected.
- Line colour indicates outcome. Width represents stock count relative to the
  starting universe. **Volume widths** switches to uniform lines.
- Click a node, outcome, or line to inspect stocks and export CSV.

Moving nodes only changes layout. Results are marked stale when screening logic,
thresholds, or the universe changes.

## Four profitability traits

Select **Load four profitability traits** in the library to load [the supplied workflow](../workflows/profitability_traits.json). This replaces the current canvas and clears its displayed run; save your workflow first if you want to keep it. The preset starts with the S&P 500 and routes Pass through TTM ROE >= 15%, TTM ROA >= 10%, ROE change over three years > 0pp, and TTM ROCE >= 30%, then into a shortlist.

Each screen is also available independently in the library. Edit `min_percent` on a node: 15 means 15% for ROE, while 5 means a change greater than 5 percentage points for the improvement screen. Its default rule is strict: unchanged ROE fails at zero. Explicit **Score ≥** and **Score ≤** overrides use their selected inclusive comparison.

Under **Universe eligibility filters**, **Excluded sectors** accepts comma-separated full sector names, matched without case sensitivity. The preset lists Financial Services / Financials, Energy, Utilities, Basic Materials / Materials, and Real Estate. Unknown or missing sectors go to the source node's Unavailable outcome when exclusions are enabled; excluded sectors go to Fail. Clear the field to allow every sector. Other universes and independent profitability nodes have no sector exclusions unless configured.

Open a stock for the shared profitability panel and its CSV export; **Compare** includes all four metrics and the comparison dates. Expand **TTM profitability calculation** in a result to inspect its inputs and reasons. Stock cards use fixed video reference thresholds; the saved workflow step records the actual rule applied in that run. [Definitions and data requirements](guides/profitability_traits.md).

## Thresholds and snapshots

Each screener starts with its existing default rule. Ordinary score-based nodes may override the final
decision using `Score ≥` or `Score ≤`. Constructor settings exposed by the
screener can be edited in the side panel. TAM uses all hard checks and disables score overrides; its priority score is independent of eligibility.

With **Reuse calculated scores** enabled, later runs can reuse the most recent
bounded in-memory snapshot. Threshold-only changes avoid FMP calls. Constructor
changes create a new score key, including edits to profitability `min_percent`. An explicit score-criterion edit can reuse the existing score. The server retains five snapshots and up to 100,000
non-error scores per snapshot; restarting clears them. FMP disk caching still applies.

## CLI compatibility

Save a workflow and run it without the web interface:

```powershell
python main.py --workflow workflow.json --output output --limit 20
```

This writes `workflow_results.json`, `workflow_report.md`, and
`workflow_summary.txt`. JSON contains node outcomes and connection counts; reports
contain stocks connected to shortlist nodes. Existing CLI commands are unchanged.
An example is provided at `workflows/value_quality.json`.

Pass and Fail mean a score and decision were returned. Unavailable means required
data or a valid score was absent. Error means processing raised; full details remain
in the local log. Cancellation takes effect between stocks.

## Tests

```powershell
.venv-ui\Scripts\python.exe scripts/run_offline_regressions.py
cd web
npm test
npm run build
```

Python tests block network access and use temporary storage.

## Broad quantitative discovery

Choose **FMP listed: US, TSX and TSXV** for the new listing universe or supply custom symbols. Add **Proven Technology / Emerging TAM** as one box and edit its defaults in the inspector. No theme keywords or Technology-sector inclusion gate apply.

Each completed TAM node shows **Settings used in this run**, per-company checks and penalties, and summary/candidate/near-miss/full-audit JSON exports. Up to 250 candidates and 100 near misses are selected for export; every eligible survivor remains on the Pass branch. Unknown required data goes to Unavailable. All results remain in the audit.

The ordinary Near misses tab is designed for single numeric thresholds. TAM's multi-rule review queue is its dedicated near-miss export. Universe prefilters and upstream boxes can remove companies before TAM evaluates them; its funnel counts describe its own input. Its exchange parameter cannot expand the chosen input universe.

[Openable example workflow](../workflows/proven_technology_emerging_tam.json), [complete checks and defaults](guides/proven_technology_emerging_tam.md). The editor normally supports 10,000 symbols, with up to 25,000 for `fmp_listed`.
