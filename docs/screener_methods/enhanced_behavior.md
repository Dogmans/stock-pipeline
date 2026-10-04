# Result and threshold behaviour

Scored rows often include both passing and failing companies. `meets_threshold` records eligibility; score sorting only orders rows. The base screen can omit missing data or invalid scores, so standalone results are not necessarily a complete input audit.

Workflow execution retains absent evaluations as Unavailable and raised processing failures as Error. Normal Markdown/text reporting selects passing rows and does not substitute top-scoring failures when fewer than the display limit pass.

```python
from utils import run_screener
results = run_screener('quality', universe_df)
passing = results.loc[results['meets_threshold'].eq(True)] if not results.empty else results
```

TAM retains every input, with independent hard-rule and scoring-penalty records. Export selection caps do not change eligibility. [TAM details](../guides/proven_technology_emerging_tam.md).

Legacy average-rank combined functions intersect returned rows, including scored failures when a component returns them; that does not prove all component thresholds passed. [Combined semantics](combined.md).
