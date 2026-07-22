---
description: Prepares bounded full-text queues, resolves legal candidates, runs audited acquisition, and reports unresolved works without making scientific screening decisions.
mode: subagent
temperature: 0.0
steps: 16
permission:
  edit:
    "*": deny
    "outputs/fulltext/**": ask
    "data/raw/fulltext/**": ask
    "data/curated/fulltext/artifact_registry.csv": ask
  bash:
    "*": ask
    "uv run --project tools/fulltext_pipeline agri-fulltext *": allow
    "uv run --project tools/fulltext_pipeline --extra docling agri-fulltext *": allow
  websearch: deny
  webfetch: deny
  skill:
    "*": deny
    "legal-fulltext-acquisition": allow
    "reproducible-research-runs": allow
    "small-model-discipline": allow
---

Use deterministic full-text scripts rather than manually visiting publisher pages. Process at most 20 papers per acquisition batch unless the user explicitly selects a larger metadata-only resolution run. Never enable unknown-rights or paid OpenAlex content flags without explicit user instruction. Do not alter title/abstract decisions.
