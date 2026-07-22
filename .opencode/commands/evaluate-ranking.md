---
description: Compare the full-text priority queue with source-located full-text outcomes and the original screening order.
agent: reproducibility-reviewer
subtask: true
---

Load `fulltext-evidence-prioritization` and `reproducible-research-runs`.

Run:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . evaluate $ARGUMENTS
```

Report, for recommended, science, fast-ROI, information-gain, and original screening order:

- core precision and recall at 20, 40, and 80;
- graded NDCG;
- cumulative evidence gain;
- papers to first core paper;
- normalized average time to core evidence;
- dataset and theme coverage.

Do not revise weights automatically. A new protocol version requires a recorded research decision and preservation of the v1 baseline.
