---
description: Prepare the highest-priority currently unscored included papers for bounded semantic evidence-priority scoring.
agent: evidence-ranker
subtask: true
---

Load `fulltext-evidence-prioritization` and `small-model-discipline`.

Run:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . prepare --range "$ARGUMENTS"
```

When `$ARGUMENTS` is empty, prepare the first 20 unscored papers in the latest hybrid ranking, or the bootstrap ranking when no hybrid run exists. A supplied range is interpreted over the **currently unscored priority queue**, not the original snowball rank.

Report the created batch directory, source ranking, candidate count, and remaining unscored count. Do not score papers in this command.
