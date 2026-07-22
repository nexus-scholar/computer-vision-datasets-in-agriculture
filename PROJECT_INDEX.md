# Project index

## Research question

Which recent or underused agricultural computer-vision datasets provide a credible opportunity for methodological novelty, and which falsifiable benchmark or model study can demonstrate that novelty rigorously?

## Active thesis

Agricultural datasets increasingly include multiple sensors, spectral channels, locations, seasons, time points, and 3D information, while many methods still assume complete, clean, fixed inputs. The project is testing whether this recurring gap justifies reliability-aware, sensor-aware segmentation rather than another clean-input backbone comparison.

## Current phase

**Title/abstract screening.** The frozen queue has 560 candidates and ranks 1–60 are complete. The next batch is 61–80.

## Sources of truth

| Layer | Path | Status |
|---|---|---|
| Seed PDFs | `data/raw/seed_papers/` | Immutable local evidence |
| Provider runs | `outputs/snowball_*` | Historical generated evidence |
| Frozen graph | `outputs/accepted_graph_2026-07-22/` | Conditional screening snapshot |
| Frozen queue | `outputs/screening_queue_2026-07-22/` | Rank-stable screening input |
| Decision history | `data/curated/screening/title_abstract_decision_history.csv` | Append-only |
| Active decisions | `data/curated/screening/title_abstract_decisions.csv` | Derived active state |
| Full-text evidence | `data/curated/evidence/` | Not yet populated |
| Dataset intelligence | `data/curated/datasets/` | Pending full-text evidence |
| Claim ledger | `data/curated/claims/` | Pending source-located evidence |

## Immediate workflow

1. Validate repository and screening state.
2. Run `/screen-paper 61-80`.
3. Continue in batches of at most 20.
4. Build a full-text queue from include/unclear decisions.
5. Extract one paper at a time into normalized evidence tables.
6. Rank datasets only after actual experimental use and access/licensing are verified.
7. Freeze one study protocol before implementing SARA-Lite or a full architecture.

## Cleanup audit

The structural migration and preserved-progress details are recorded in `docs/project/REPOSITORY_AUDIT_2026-07-22.md`, `PRESERVED_PROGRESS_2026-07-22.md`, and `CLEANUP_MIGRATION_2026-07-22.md`.
