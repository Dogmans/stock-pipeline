# Legacy turnaround tests

The implementation under test is `screeners.turnaround_candidates.screen_for_turnaround_candidates`, not a registered workflow node.

```powershell
.venv-ui\Scripts\python.exe -m unittest tests.test_turnaround_screener tests.test_turnaround_screener_logic
```

These legacy test modules use mocked provider inputs but are outside the normal targeted regression runner; older assertions may describe earlier behaviour. Full test discovery also includes live integrations. [Current testing policy](../testing.md).

When constructing new fixtures, use normalized `totalRevenue`, `grossProfit`, `eps`, `cash`, `totalDebt`, and datetime `fiscalDateEnding`, sorted newest first. Use at least the configured six quarters. Pass requires score at least 5; returned rows can also include scored failures. Test recovery patterns against steady growth, missing fields and insufficient history rather than assuming every returned row is a candidate.

[Turnaround policy and current score weights](../guides/turnaround_screener.md), [FMP fields](../provider_guides/fmp_field_reference.md).
