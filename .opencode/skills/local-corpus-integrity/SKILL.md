---
name: local-corpus-integrity
description: Verify that each local PDF maps to the intended seed paper using hashes, first-page metadata, stable identifiers, and a non-destructive filename plan.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: corpus
---

For every local paper record, capture seed ID, source path, SHA-256, byte size, page count, visible title, authors, year, DOI/arXiv/PMID/PMCID, identity status, and evidence.

Statuses: `verified`, `manual_review`, `duplicate_bytes`, `wrong_paper`, `missing`, `unmapped`.

Never edit PDF bytes. Prefer a curated mapping manifest over destructive renaming. If human-readable copies are later created, use `P###__short-title__year.pdf`, retain the source hash, and record source-to-copy lineage.
