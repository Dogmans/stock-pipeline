# Stock Pipeline architecture

Core architecture reviewed on 2026-10-04; profitability components and integration updated on 2026-10-27. Start with [README.md](README.md) for installation and [the documentation index](docs/README.md) for topic guides.

## Execution paths

The standalone CLI in `main.py` resolves a universe, gathers market context, runs selected registered screeners independently, and writes Markdown/text reports. A comma-separated strategy list is not a sequential filter chain. Normal `--strategies all` excludes opt-in research screens.

The editor API in `visual_api.py` and `main.py --workflow` use `WorkflowEngine` in `workflow.py`. The engine validates a rooted graph, evaluates each screener per input symbol, routes Pass/Fail/Unavailable/Error outcomes, and records node rules, stock evidence and connection counts. It supports source fan-out but no cycles or merges. Output nodes collect their incoming records; connecting a Fail branch to an output deliberately selects failures.

## Components

| Path | Responsibility |
| --- | --- |
| `universe.py` | Index constituents, index union, ETF-derived country sets and `fmp_listed` discovery listings |
| `utils/screener_registry.py` | Explicit class registration, construction, catalog and default strategy selection |
| `screeners/base_screener.py` | Common screener interface, data fetching and result assembly |
| `screeners/` | Registered class implementations and separate legacy function modules |
| `data_providers/financial_modeling_prep.py` | Existing FMP overview, statements, prices and auxiliary endpoints |
| `data_providers/fmp_screening.py` | Stable FMP discovery access, eight-quarter requests, FX and bounded retries |
| `screening_audit.py` | TAM funnel, benchmarks, candidate/near-miss selection and JSON exports |
| `cache_config.py` | DiskCache FanoutCache under `data/cache`, with eight shards |
| `utils/rate_limiter.py`, `utils/throttling.py` | Request-level limits and selected method-level throttling |
| `reporting.py` | Passing-stock Markdown/text reports |
| `web/src/` | React flow editor, inspections, ranking and research controls |
| `profitability.py` | Shared TTM ROE/ROA/ROCE history and three-year ROE comparison from reported quarterly statements |
| `screeners/profitability.py` | Four opt-in numeric screens using the shared profitability calculations |
| `web/src/ProfitabilityPanel.jsx` | Shared metric cards, historical chart and profitability CSV export |
| `research.py` | Local run history, research snapshots, financial history and forward price tracking |
| `technical_indicators.py`, `visualization.py` | Supporting analysis/legacy visualization utilities; not the default report pipeline |

## Results and eligibility

Most class screeners return scored rows with `meets_threshold`, including failures. The base class can skip missing data or invalid scores; it does not guarantee one row per symbol. Workflow execution turns absent evaluations into explicit Unavailable outcomes and raised processing failures into Error outcomes. The reporting layer displays passing rows only and does not fill short reports with failed stocks.

TAM overrides the base evaluation path to retain every input and evaluates multiple hard checks independently of its research-priority score. Its default rule cannot be replaced with a score threshold. Every run retains effective settings, raw statement rows, calculations and rule evidence. See [the TAM guide](docs/guides/proven_technology_emerging_tam.md).

The registry contains 20 screens; 15 are selected by default. The four profitability screens are opt-in and share `profitability.py` with `StockDetailService` in `visual_api.py`. Stock detail responses contain a separate `profitability` object with the latest observation, history and methodology. Each profitability screen uses four quarters of profit and closing balance-sheet values; unavailable inputs remain separate from failed thresholds. The improvement screen uses a strict `gt` default rule, while generic score overrides remain inclusive. [Definitions and API fields](docs/guides/profitability_traits.md).

Universe filters run before node evaluation and include comma-separated sector exclusions. The four-trait preset sets those exclusions; the individual screens do not. Saved results retain the per-node rules and calculation evidence.

The existing `composite_score` is a weighted numeric factor screener. Legacy combined functions rank intersection membership in returned result sets; that is not the same as passing every component threshold or a grouped workflow node.

## Providers and configuration

Registered screeners normally initialize their own FMP provider. Standalone `--data-provider` selects the provider passed to market-context collection; it does not rewire those screener instances. Configuration is split between `config.py`, constructor defaults and implementation constants. The editor derives editable parameters from constructor signatures.

FMP overview fields are assembled from legacy endpoints and may be missing or conditional. Legacy statement columns are normalized; ratios are generally decimals. `get_research_statements()` supplies raw stable statements separately, up to ten annual periods or forty quarters, cached for 24 hours. The profitability adapter uses quarterly income and balance statements from that path without changing legacy statement lookbacks. Discovery uses isolated stable endpoints without migrating existing consumers. [Provider guide](docs/provider_guides/financial_modeling_prep.md).

## Persistence and freshness

Disk cache entries persist across processes and expire per method. In-memory score snapshots are bounded and disappear when the API restarts. Completed editor history persists separately in `output/workflow_history`. Restoring history does not refresh its data. A new score snapshot still uses the disk cache.

Many existing refresh methods clear the entire cache. `clear_old_cache` is not selective age deletion: under 168 hours it does nothing; at least 168 hours clears everything. [Cache guide](docs/cache_usage.md).

## Extending the application

Subclass `BaseScreener`, register the class explicitly, and expose simple constructor parameters for the editor. Verify catalog default rules and sorting direction. If eligibility depends on multiple rules, keep eligibility separate from score and preserve unknown outcomes. Add mocked behavioural tests to the offline suite where appropriate. [Package guide](docs/screener_methods/package_structure.md), [testing guide](docs/testing.md).
