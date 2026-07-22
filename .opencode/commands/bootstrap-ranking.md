---
description: Build an immediate deterministic full-text priority queue for every active title/abstract inclusion, without changing screening decisions or requiring model scoring.
agent: evidence-ranker
subtask: true
---

Load `fulltext-evidence-prioritization` and `reproducible-research-runs`.

Run:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . bootstrap
```

Report:

- included-paper count;
- AI-score count, which should be zero in bootstrap mode;
- the four main rank views;
- top-20 papers;
- theme and dataset diversity;
- Pareto-front papers;
- rank-stability warnings;
- output directory and manifest hashes.

Do not change title/abstract screening decisions. Bootstrap values are scheduling estimates, not curated paper evidence.
