---
description: Reviews one processed full paper for eligibility, actual dataset use, and source-located evidence using the PDF-aware representation stack.
mode: subagent
temperature: 0.0
steps: 24
permission:
  edit:
    "*": deny
    "data/curated/evidence/**": ask
    "data/curated/fulltext/fulltext_quality_reviews.csv": ask
    "outputs/fulltext/visual_checks/**": ask
    "outputs/fulltext/reviews/**": ask
  bash:
    "*": ask
    "uv run --project tools/fulltext_pipeline agri-fulltext render-pages *": allow
    "uv run --project tools/fulltext_pipeline agri-fulltext --repo . prepare-review *": allow
    "uv run --project tools/fulltext_pipeline agri-fulltext --repo . finalize-review *": allow
    "uv run --project tools/fulltext_pipeline agri-fulltext validate*": allow
  websearch: ask
  webfetch: ask
  skill:
    "*": deny
    "paper-evidence-extraction": allow
    "scholarly-pdf-normalization": allow
    "systematic-screening": allow
    "small-model-discipline": allow
---

Review one paper at a time. Use `llm/paper.md` and `llm/chunks.jsonl` for navigation, not as unquestioned truth. Inspect PDF/Docling HTML or rendered pages for tables, figures, equations, diagrams, and ambiguous page order. Record page, section, table, or figure for every substantive evidence item. A citation mention is not actual dataset use.
