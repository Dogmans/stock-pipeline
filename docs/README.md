# Documentation

The core guide review dates from 2026-10-04; profitability metrics, screeners and related references were updated against the code on 2026-10-27. Dated development notes and implementation reports are historical records, not current setup instructions.

## Start here

- [Project README](../README.md): installation, editor and CLI quick start.
- [Architecture](../DOCUMENTATION.md): execution paths, providers and extension points.
- [Visual editor](visual_editor.md): graph mechanics, settings and snapshots.
- [Stock research](stock-research.md): ranking, comparisons, histories and performance.
- [Four profitability traits](guides/profitability_traits.md): TTM ROE, ROA, ROCE, three-year ROE change, screening preset, API fields and CSV units.
- [TAM candidate screen](guides/proven_technology_emerging_tam.md): quantitative checks, penalties and audit exports.
- [Research workflow](investment_workflow.md): broad candidate discovery followed by qualitative review.

## Reference

- [Strategy IDs and defaults](screener_methods.md), [strategy names](screener_methods/strategy_names.md).
- [Package structure](screener_methods/package_structure.md), [result behaviour](screener_methods/enhanced_behavior.md).
- [PEG](screener_methods/peg_ratio.md), [insider buying](screener_methods/insider_buying.md), [legacy combined functions](screener_methods/combined.md).
- [Providers](provider_guides.md), [FMP implementation](provider_guides/financial_modeling_prep.md), [field reference](provider_guides/fmp_field_reference.md).
- [Data processing](data_processing.md), [cache semantics](cache_usage.md), [reporting](guides/reporting.md).
- [Testing](testing.md), [PowerShell commands](powershell_commands.md), [scripts](../scripts/README.md).
- [Legacy turnaround guide](guides/turnaround_screener.md), [turnaround tests](testing/turnaround_screener_testing.md), [legacy sector corrections](sector_corrections.md).
- [Current screener status](SCREENER_STATUS.md).

## Historical material

- [Development notes](daily_notes/README.md).
- [Earlier refactoring report](architecture/screener_refactoring.md).
- [BaseScreener implementation report](../BASESCREEN_IMPLEMENTATION.md).
- [Dated FMP performance investigation](fmp_performance.md). Its timings are sample measurements, not current performance guarantees.
