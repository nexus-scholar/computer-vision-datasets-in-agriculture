---
description: Build the hybrid scientific, fast-ROI, information-gain, Pareto, sensitivity, and diversity-aware full-text queues. AI-scored papers use curated scores; all others retain deterministic bootstrap fallback values.
agent: evidence-ranker
subtask: true
---

Load `fulltext-evidence-prioritization` and `reproducible-research-runs`.

Run:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . build
```

Report:

- included count;
- AI semantic-score coverage;
- bootstrap-fallback coverage;
- top 20 recommended papers;
- all rank views;
- theme/dataset coverage;
- Pareto-front count;
- stable, moderate, and unstable rank counts;
- top-20 scenario frequencies;
- run directory and source hashes.

Do not treat sensitivity frequencies as probabilities of scientific truth. Do not change any screening decision.
