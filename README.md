# Agricultural Computer-Vision Dataset Research Workspace

This repository supports a citation-guided study of recent and underused computer-vision datasets in agriculture, followed by a rigorously gated methodology study. The active research emphasis is robust segmentation, multimodal and spectral sensing, cross-sensor generalization, calibration, and sensor-aware reliability.

## Current checkpoint

- 13 seed dataset papers are locally available and identity-mapped.
- One-hop OpenAlex and Semantic Scholar snowballing has been collected and repaired.
- The frozen screening queue contains 560 canonical candidates.
- All 560 candidates have active AI title/abstract decisions under a human-authorized protocol.
- Current active counts: 260 include, 300 exclude, 0 unclear.
- Title/abstract screening is complete. The next stage is evidence-priority ranking,
  lawful full-text acquisition, full-text eligibility, and source-located extraction.

The screening queue is intentionally frozen so existing rank-based progress remains stable. Its accepted graph is conditionally usable for screening but not for citation-coverage claims because Semantic Scholar reference retrieval is incomplete for P001 and P007.

## Start here

```powershell
uv sync
uv run pytest
python scripts/research/screening_state.py validate --repo .
```

OpenCode:

```text
/status
/ranking-status
/bootstrap-ranking
```

The paper-priority workflow orders all 260 inclusions for full-text work without changing screening decisions. Do not hand-edit the active screening CSV.

## Important paths

| Path | Purpose |
|---|---|
| `data/raw/seed_papers/` | Immutable local seed PDFs plus identity/hash manifest |
| `data/raw/citation_exports/` | Citation tables extracted from the original report |
| `data/raw/api_archives/` | Compressed historical API response caches |
| `data/curated/bibliography/` | Seed/provider identity decisions |
| `data/curated/screening/` | Decision history, active decisions, relevance tags, and batch provenance |
| `outputs/accepted_graph_2026-07-22/` | Frozen accepted provider graph used to create the queue |
| `outputs/screening_queue_2026-07-22/` | Frozen canonical queue with ranks 1–560 |
| `outputs/screening_batches/` | Validated per-batch artifacts |
| `scripts/research/` | Deterministic audit, screening, and graph utilities |
| `.opencode/` | Bounded agents, skills, and commands |
| `docs/project/CURRENT_STATE.md` | Current blockers, progress, and exact next action |
| `docs/project/REPOSITORY_AUDIT_2026-07-22.md` | Defects found, repairs made, retained limitations, and validation |

## Screening state

The screening layer is normalized:

- `title_abstract_decision_history.csv` is append-only and preserves superseded decisions.
- `title_abstract_decisions.csv` is the active 560-row snapshot.
- `title_abstract_relevance.csv` is a derived wide tag table.
- `title_abstract_decisions_enriched.csv` is the human-readable joined view; it is regenerated, never edited.
- `screening_batches.csv` links each decision batch to an immutable queue hash and screened-row hash.

Validate at any time:

```powershell
python scripts/research/screening_state.py validate --repo .
```

## Snowball collection

The collector remains under `tools/agri_cv_snowball_package/`. Use the root `uv` environment and a fresh dated output directory:

```powershell
$env:OPENALEX_API_KEY = "..."
$env:OPENALEX_MAILTO = "you@example.com"
$env:S2_API_KEY = "..."

uv run python tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py `
  --input tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --out outputs/snowball_<purpose>_<YYYY-MM-DD> `
  --providers both
```

Never overwrite historical runs or rebuild the active screening queue in place. The frozen accepted graph, queue, batch artifacts, audits, and inventory are intentionally allowed through `.gitignore` so the current screening state can be committed; bulk provider runs remain local by default.

## Research gate

Title/abstract screening is discovery, not evidence extraction. Dataset ranking and study design should wait until full-text papers have source-located evidence for actual dataset use, available modalities, evaluation splits, robustness tests, limitations, and access/licensing.
