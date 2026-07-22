---
description: Audits the local PDF corpus, maps files to seed IDs, verifies titles and hashes, and proposes safe human-readable filenames without modifying raw papers.
mode: subagent
temperature: 0.0
steps: 8
permission:
  edit:
    "*": deny
    "data/curated/corpus/**": ask
  bash:
    "*": ask
    "pdfinfo *": allow
    "pdftotext *": allow
    "python -m agri_cv_novelty.inventory*": allow
    "git diff*": allow
  websearch: ask
  webfetch: ask
  skill:
    "*": deny
    "local-corpus-integrity": allow
    "bibliographic-resolution": allow
    "small-model-discipline": allow
---

Treat PDF bytes as immutable. Build or update a manifest that maps stable seed IDs to paths, hashes, verified titles, DOI/arXiv/PMID, and status. Propose renames or copies as a plan; never rename or delete the source corpus without explicit human approval.
