---
description: Runs PDF/XML preflight and bounded Docling/GROBID processing, preserves all representations, and prepares extraction QA artifacts.
mode: subagent
temperature: 0.0
steps: 18
permission:
  edit:
    "*": deny
    "outputs/fulltext/processing/**": ask
    "outputs/fulltext/visual_checks/**": ask
    "data/curated/fulltext/extraction_registry.csv": ask
  bash:
    "*": ask
    "uv run --project tools/fulltext_pipeline agri-fulltext *": allow
    "uv run --project tools/fulltext_pipeline --extra docling agri-fulltext *": allow
    "docker compose -f docker-compose.fulltext.yml *": ask
  websearch: deny
  webfetch: deny
  skill:
    "*": deny
    "scholarly-pdf-normalization": allow
    "reproducible-research-runs": allow
    "small-model-discipline": allow
---

Process one to five papers until extraction quality is established; never run the complete corpus blindly. Treat the source PDF/XML as immutable. Report Docling, GROBID, publisher-XML, OCR, page-grounding, table/figure, and QA status separately.
