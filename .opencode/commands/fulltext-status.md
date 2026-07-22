---
description: Show legal full-text acquisition and processing coverage.
agent: fulltext-acquirer
subtask: true
---

Read `docs/workflow/FULLTEXT_WORKFLOW.md`, then run:

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . status
uv run --project tools/fulltext_pipeline agri-fulltext --repo . validate
```

Report eligible works, PDFs, structured XML, processed papers, QA statuses, rights statuses, pending acquisition, pending processing, and validation errors. Do not alter the repository.
