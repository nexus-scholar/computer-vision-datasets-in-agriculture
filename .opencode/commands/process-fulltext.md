---
description: Process a small rank range with preflight, Docling, GROBID, normalization and QA.
agent: document-processor
subtask: true
---

Process ranks `$ARGUMENTS`.

1. Read `docs/workflow/FULLTEXT_WORKFLOW.md` and `PDF_REPRESENTATION_POLICY.md`.
2. Confirm GROBID health and Docling availability.
3. Start with at most five papers while the workflow is new.
4. Run:

```powershell
uv run --project tools/fulltext_pipeline --extra docling agri-fulltext --repo . process --ranks "$ARGUMENTS"
```

5. Run full-text validation.
6. Report each paper's source artifacts, PDF class, preferred text/chunk source, Docling status, GROBID status, tables/figures, QA status, and visual-review need.

Do not classify scientific eligibility or actual dataset use in this command.
