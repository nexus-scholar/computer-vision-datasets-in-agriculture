---
name: scholarly-pdf-normalization
description: Convert scholarly PDF/XML into auditable layout-aware, citation-aware, and LLM-friendly representations while preserving the original source and page-grounding requirements.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: fulltext
---

Maintain a representation stack, not one flattened text file:

- original PDF/publisher XML: ground truth;
- publisher JATS XML: preferred semantic text;
- Docling JSON/HTML: layout, tables, figures, page provenance;
- GROBID TEI: scholarly header, references, citation contexts and coordinates;
- Markdown: reading view;
- JSONL chunks: retrieval view.

Before conversion classify the PDF as born-digital, hybrid, scanned, encrypted, or corrupt.

Rules:

- Use OCR only when preflight indicates it is needed.
- Keep original and OCR-derived artifacts separate.
- Preserve captions with figures/tables.
- Do not treat Markdown tables as proof that table structure is correct.
- For every table, figure, equation, and page-sensitive claim, require PDF/HTML/JSON visual verification.
- Chunks must retain source SHA-256, section path, pages where available, parser/version, and visual-review flags.
- Do not vector-index a failed or unreviewed extraction.
- Never silently replace a processed representation; create a new run tied to the source hash.
