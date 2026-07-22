---
description: Score one prepared evidence-priority batch, finalize it into append-only curated history, and rebuild the hybrid full-text queue.
agent: evidence-ranker
subtask: true
---

Load `fulltext-evidence-prioritization`.

`$ARGUMENTS` should be a prepared batch directory. When empty, use the newest pending directory under `outputs/fulltext_ranking/scoring_batches/`.

1. Read only `input_rows.csv`, `scored_rows_template.csv`, and `batch_manifest.json` from that batch.
2. Independently apply the skill rubric. Bootstrap columns are hints about scheduling, not answers to copy.
3. Fill every row in `scored_rows.csv` using the exact template schema.
4. Preserve `candidate_id`, `included_order`, `original_screening_rank`, and `title` exactly.
5. Use integer semantic scores only.
6. Set `reviewer=opencode_ai`, record the active model, use `protocol_version=EVIDENCE_ROI_V1`, and record a UTC timestamp.
7. Run:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . finalize-batch --batch "$ARGUMENTS"
```

8. If finalization passes, rebuild:

```bash
uv run python scripts/research/fulltext_ranking.py --repo . build
```

9. Stop if validation fails. Never change a screening decision or automatically process another batch.
