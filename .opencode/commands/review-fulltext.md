---
description: Review one processed full paper for eligibility and source-located dataset evidence.
agent: fulltext-reviewer
subtask: true
---

Review rank or paper ID `$ARGUMENTS`. Process exactly one paper.

1. Prepare a deterministic review workspace:

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . prepare-review "$ARGUMENTS"
```

2. Read the generated `review_context.json`, then inspect `llm/paper.md`, `llm/chunks.jsonl`, references, tables, figures, and formulas inventories.
3. Inspect the original PDF or Docling HTML/JSON for every table, figure, equation, diagram, page-sensitive claim, or uncertain reading order.
4. Render only necessary pages.
5. Decide one of:

```text
include_core
include_supporting
exclude
unresolved
```

6. Verify the paper-dataset relationship using one of:

```text
introduced
used_training
used_evaluation
used_pretraining
extended
repackaged
benchmarked
compared_descriptively
mentioned_only
unclear
```

7. Record page, section, table, or figure for every substantive evidence item. Use `unknown` instead of inference.
8. Fill exactly one copy of `decision_template.csv` in the review workspace. Use these reason-code families:
   - `FI*` for `include_core`;
   - `FS*` for `include_supporting`;
   - `FE*` for `exclude`;
   - `FU*` for `unresolved`.
9. Finalize through the deterministic validator:

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . finalize-review <path-to-filled-decision.csv>
```

10. Do not modify title/abstract history or append directly to the curated CSV.
