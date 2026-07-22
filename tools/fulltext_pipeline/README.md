# agri-fulltext

Isolated command-line tool for legal scholarly full-text acquisition, immutable source storage, PDF/XML preflight, Docling/GROBID processing, and extraction QA.

It is designed for the agricultural computer-vision evidence repository, but all network resolution is identifier-driven and all document derivatives retain source hashes.

## Commands

```text
agri-fulltext queue
agri-fulltext resolve
agri-fulltext acquire
agri-fulltext import
agri-fulltext preflight
agri-fulltext process
agri-fulltext render-pages
agri-fulltext review-queue
agri-fulltext prepare-review
agri-fulltext finalize-review
agri-fulltext status
agri-fulltext validate
```

See `../../docs/workflow/FULLTEXT_WORKFLOW.md` for the operational sequence and rights policy.
