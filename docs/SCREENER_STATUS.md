# Current screener status

Reviewed on 2026-10-04 against the runtime registry.

- 16 class screens are registered; 15 run under the default `all` selection.
- TAM is opt-in, available as a single editable flow box with auditable hard checks and score penalties.
- ROE and selectable-period Price Change have dedicated evidence displays.
- CLI independent screening and editor/CLI workflow execution are supported.
- Turnaround, fallen IPO, sector correction and average-rank combined functions remain separate legacy modules, not registered flow boxes.

[Strategy IDs, rules and parameters](screener_methods.md), [architecture](../DOCUMENTATION.md), [TAM guide](guides/proven_technology_emerging_tam.md).

## Validation and limitations

The network-isolated regression runner covers existing reporting/transport/workflow/API behaviour and TAM. Frontend unit tests and production build are separate checks. Live FMP subscription coverage and broad-run survivor counts are not established by mocked tests. See [testing](testing.md).

Known implementation limitations are documented rather than silently repaired: overview growth is not populated; some overview ratio fields are conditional; legacy PEG `min_growth` is stored but not enforced; CLI rate-control/statistics flags are parsed but not acted on; cache age clearing is coarse. These documentation updates do not change runtime behaviour.
