# Full-text acquisition and scholarly PDF workflow

## Purpose

Acquire legal full text for title/abstract inclusions while screening continues, preserve source provenance, and create an LLM-friendly representation without discarding page layout, tables, figures, citations, or the original artifact.

## Canonical representations

The workflow deliberately keeps several representations:

1. **Original PDF or publisher XML** — evidentiary ground truth.
2. **Publisher JATS XML** — preferred semantic text when available.
3. **Docling JSON/HTML** — preferred layout, table, figure, and page-aware representation.
4. **GROBID TEI XML** — preferred scholarly structure, bibliography, and citation-context representation.
5. **Markdown** — convenient human/LLM reading view; never the canonical source.
6. **JSONL chunks** — retrieval units with source hash and page/section metadata.

Do not collapse these into a single Markdown file.

## Legal acquisition policy

Allowed automated sources:

- exact direct PDF URL already present in the accepted metadata;
- the PMC ID Converter followed by PubMed Central OAI-PMH and Europe PMC open full text;
- arXiv;
- Unpaywall OA locations;
- Crossref full-text links;
- OpenAlex OA locations;
- Semantic Scholar `openAccessPdf`;
- OpenAlex content only when explicitly enabled and rights/cost are accepted.

The pipeline performs exact-identifier resolution only. It does not scrape search-engine results, bypass paywalls, use shadow libraries, or imitate a browser to evade access controls.

A library/institutional copy may be imported manually for local research. Mark it `local_research_only` or `restricted`, keep it outside Git, and do not redistribute it.

## Parallel workflow while screening continues

At any checkpoint, build an acquisition queue from active `include` and `unclear` title/abstract decisions. For example, while ranks 161–180 are in progress, acquire completed ranks 1–160 only:

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . queue --ranks 1-160
```

Do not acquire from an unfinished batch or directly from the raw snowball graph.

## Acquisition workflow

### 1. Configure credentials

Copy relevant values from `.env.fulltext.example` into your local `.env` or PowerShell session:

```powershell
$env:UNPAYWALL_EMAIL = "you@example.com"
$env:OPENALEX_API_KEY = "..."
$env:S2_API_KEY = "..."
```

### 2. Build a queue

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . queue --ranks 1-160
```

### 3. Resolve candidates without downloading

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . resolve `
  outputs/fulltext/acquisition/queue_<timestamp>/fulltext_queue.csv
```

Inspect `candidates.csv`. Candidate scoring prefers structured XML, published versions, known OA licenses, and exact direct URLs.

### 4. Acquire both structured text and PDF

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . acquire `
  outputs/fulltext/acquisition/queue_<timestamp>/fulltext_queue.csv `
  --artifact-set both
```

The downloader validates signatures/XML, streams to temporary files, applies size limits, hashes bytes, stores immutable artifacts, and writes every attempt to both the run audit and the append-only `data/curated/fulltext/fetch_attempt_registry.csv`. Resolver failures are preserved separately in `resolver_error_registry.csv`.

### 5. Import a local lawful copy

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . import `
  "C:\Downloads\paper.pdf" `
  --rank 37 `
  --rights-status local_research_only `
  --notes "Downloaded manually through institutional library access"
```

## Processing workflow

### Start GROBID

```powershell
docker compose -f docker-compose.fulltext.yml up -d grobid
```

For the much larger full GROBID model stack, use the optional override only after the CRF workflow is stable:

```powershell
docker compose -f docker-compose.fulltext.yml -f docker-compose.fulltext.full.yml up -d grobid
```

The default CRF image is smaller. Use `grobid/grobid:0.9.0-full` only when the larger image and resource demand are acceptable and higher-quality reference/citation parsing is valuable.

### Run extraction

```powershell
uv run --project tools/fulltext_pipeline --extra docling agri-fulltext --repo . process --ranks 1-20
```

Process small batches first. Do not run hundreds of PDFs until extraction QA is stable.

### Per-paper outputs

```text
outputs/fulltext/processing/<run>/<paper>/
├── source_manifest.json
├── manifest.json
├── publisher_xml/
│   ├── document.md
│   ├── chunks.jsonl
│   ├── references.jsonl
│   ├── citation_contexts.jsonl
│   ├── tables.jsonl
│   ├── figures.jsonl
│   └── formulas.jsonl
├── docling/
│   ├── original Docling exports and referenced assets
│   └── normalized/
│       ├── document.json
│       ├── document.html
│       ├── document.md
│       ├── chunks.jsonl
│       ├── tables.jsonl
│       ├── figures.jsonl
│       └── formulas.jsonl
├── grobid/
│   ├── fulltext.tei.xml
│   └── normalized/
│       ├── document.md
│       ├── references.jsonl
│       ├── citation_contexts.jsonl
│       ├── tables.jsonl
│       ├── figures.jsonl
│       └── formulas.jsonl
├── llm/
│   ├── paper.md
│   ├── chunks.jsonl
│   ├── references.jsonl
│   ├── citation_contexts.jsonl
│   ├── tables.jsonl
│   ├── figures.jsonl
│   └── formulas.jsonl
└── qa/
    ├── preflight.json
    └── extraction_quality.json
```

## PDF treatment matrix

| Input | Primary path | Secondary path | Mandatory QA |
|---|---|---|---|
| Publisher JATS + PDF | JATS for text; PDF/Docling for layout | GROBID for citation coordinates | Compare tables/figures with PDF |
| Born-digital PDF | Docling standard pipeline | GROBID TEI | Check page grounding and multi-column order |
| Hybrid PDF | Docling with OCR | GROBID on original PDF | Inspect OCR-sensitive pages |
| Scanned PDF | Docling forced OCR | Optional OCRmyPDF derivative, then GROBID | Manual page sampling required |
| Complex tables/equations | Docling accurate tables | Marker/MinerU fallback only after failure | Visual comparison to PDF |
| Encrypted/corrupt PDF | Manual resolution | Obtain another lawful version | Do not attempt extraction until repaired |

## Evidence use rules

- Narrative text may be extracted from the preferred text source.
- Tables, figures, equations, diagrams, and page-sensitive claims must be checked against PDF/Docling HTML/JSON or a rendered page. Structured JATS table cells retain row/column spans and raw XML; Docling JSON remains the canonical extracted layout representation.
- Full-text inclusion and actual dataset use remain reviewer decisions.
- Every extracted evidence row must record page, section, table, or figure when available.
- Do not quote long passages into the curated database.

## Render pages on demand

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext render-pages `
  data/raw/fulltext/<paper>/<hash>/source.pdf `
  --pages 3-5 `
  --out outputs/fulltext/visual_checks/<paper>
```

Do not render every page of every paper by default.

## Build the full-text review queue

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . review-queue
```

Review one paper at a time. The OpenCode command creates a deterministic workspace and validates the final event:

```text
/review-fulltext <rank>
```

The underlying commands are:

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . prepare-review <rank>
uv run --project tools/fulltext_pipeline agri-fulltext --repo . finalize-review <filled-decision.csv>
```

Never edit `data/curated/screening/full_text_decisions.csv` directly.

## Validation

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . status
uv run --project tools/fulltext_pipeline agri-fulltext --repo . validate
uv run pytest
```
