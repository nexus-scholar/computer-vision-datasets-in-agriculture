---
description: Show included-paper count, semantic score coverage, bootstrap fallback coverage, full-text outcomes, latest ranking runs, and the exact next action.
agent: evidence-ranker
subtask: true
---

Run:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . status
```

Return the concise status and next command only.
