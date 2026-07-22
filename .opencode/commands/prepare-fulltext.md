---
description: Build a bounded legal full-text acquisition queue from completed title/abstract decisions or a ranking CSV.
agent: fulltext-acquirer
subtask: true
---

Prepare ranks `$ARGUMENTS`. If blank, use all currently completed `include` and `unclear` decisions. If `$ARGUMENTS` is a CSV file path, use it as a ranking source with `--ranking` mode.

1. Read `docs/workflow/FULLTEXT_WORKFLOW.md` and the legal acquisition skill.
2. Do not include an unfinished screening batch.
3. Run:

```powershell
if ($args[0] -match '\.csv$') {
  uv run --project tools/fulltext_pipeline agri-fulltext --repo . queue --ranking "$ARGUMENTS"
} elseif ($ARGUMENTS) {
  uv run --project tools/fulltext_pipeline agri-fulltext --repo . queue --ranks "$ARGUMENTS"
} else {
  uv run --project tools/fulltext_pipeline agri-fulltext --repo . queue
}
```

4. Run `resolve` on the new queue but do not download.
5. Report candidate coverage by source, structured/PDF availability, rights-status warnings, identifiers missing, and the exact acquisition command. Do not enable OpenAlex content or unknown-rights flags.
