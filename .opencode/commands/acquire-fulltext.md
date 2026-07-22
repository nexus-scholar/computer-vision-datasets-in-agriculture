---
description: Acquire legal structured text and PDF artifacts for one prepared queue.
agent: fulltext-acquirer
subtask: true
---

`$ARGUMENTS` must be the path to one prepared `fulltext_queue.csv`.

1. Inspect its queue manifest and candidate-resolution output.
2. Refuse to use raw snowball nodes or unfinished screening rows.
3. Run:

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . acquire "$ARGUMENTS" --artifact-set both
```

4. Validate the full-text state.
5. Report successes, source distribution, structured/PDF coverage, skipped-rights records, failures, and manual-resolution candidates.

Never use `--allow-unknown-rights`, enable paid content, or import local files without explicit user authorization.
