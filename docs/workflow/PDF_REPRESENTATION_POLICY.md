# PDF representation policy

## The source of truth

The original PDF or publisher XML is immutable. Every derivative records its source SHA-256 and processor version.

## Why one format is insufficient

- PDF preserves visual truth but is poor for direct semantic processing.
- Markdown is readable but loses layout and may flatten tables.
- Docling JSON preserves a hierarchical document model, provenance, table spans, pictures, formulas, and layout.
- HTML is convenient for visual inspection of extracted structure.
- GROBID TEI specializes in scholarly metadata, bibliography, and citation contexts.
- JSONL chunks are optimized for retrieval but are lossy views.

## Preferred hierarchy

1. Publisher JATS XML for prose, section structure, references, and explicit tables.
2. Docling JSON for page/layout grounding and tables/figures.
3. GROBID TEI for bibliography and in-text citation links.
4. Docling Markdown for reading.
5. OCR-derived text only when no reliable born-digital text exists.

## Chunking

Chunks must:

- preserve section hierarchy;
- retain source SHA-256 and parser/version;
- include page start/end where available;
- never split a table as ordinary prose;
- keep captions with tables/figures;
- flag chunks requiring visual verification;
- store citation/reference links separately from raw text.

Do not embed or vector-index the corpus until extraction QA passes. A vector database is an optional downstream index, not a source-of-truth store.


## Visual and mathematical objects

Keep table, figure, and formula inventories separate from ordinary prose chunks. Publisher XML inventories retain raw XML and structured JATS table cells; Docling inventories retain raw layout objects and provenance; GROBID inventories retain available TEI coordinates. Referenced visual assets are copied beside the normalized Docling HTML/Markdown views so those derivatives remain inspectable.
