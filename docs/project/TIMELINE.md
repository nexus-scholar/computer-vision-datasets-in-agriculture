# Project timeline: how we got here

A narrative history of the agricultural-CV dataset research program, from the
original seed corpus to the closed full-text universe and the refreshed
synthesis layer. Every claim here points to a durable artifact; nothing is
written from memory.

The story is told in phases. Each phase names the frozen/immutable evidence
that proves it happened.

## Phase 0 - The starting point: 13 seeds and a question

The program began as a citation-guided study: find recent, *underused*
computer-vision datasets in agriculture, then turn the best candidates into a
rigorously gated methodology study. The research emphasis was defined up front:
robust segmentation, multimodal and spectral sensing, cross-sensor
generalization, calibration, and sensor-aware reliability.

The starting material was 13 seed dataset papers, each locally available and
identity-verified from its PDF:

- P001 MuST-C (Sci Data), P002 TomatoMAP (Sci Data), P003 AgriVision (Sci Data)
- P004 MFO (CVPRW), P005 Horti-M3-Tomato (Sci Data), P006 Broad-Leaf-Legumes-3D
- P007 BAWSeg (MDPI RS), P008 SoyCotton (Sci Data), P009 TomatoWUR (DIB)
- P010 WeedsGalore (WACV), P011 PlantSeg (Sci Data), P012 MFWD (Sci Data), P013 TomatoPGT (DIB)

Evidence: `data/raw/seed_papers/manifest.csv` (sha256-verified) and the PDFs
themselves.

One correction was made here that shaped the audit culture of the project:
**P004** had a false OpenAlex identity match (a different paper on the same
name). The seed was re-resolved; the historical edges were quarantined, not
deleted. The same discipline — never silently overwrite, always append a
superseding event — later became the project's frozen-state rule.

## Phase 1 - Snowballing: from 13 seeds to a 560-paper universe

One-hop snowball collection ran against OpenAlex and Semantic Scholar, was
repaired, and a second S2 retry was preserved. The result was a frozen
**accepted graph with 869 provider citation relations** and a canonical
**screening queue of 560 ranked candidates**.

Evidence: `outputs/accepted_graph_2026-07-22/`,
`outputs/screening_queue_2026-07-22/screening_queue.csv` (sha256-pinned),
`data/raw/api_archives/` (compressed historical API caches), and the
reproducibility audit `docs/project/REPOSITORY_AUDIT_2026-07-22.md`.

Known, accepted limitation: the graph was built with
`allow_incomplete_relations=true` and Semantic Scholar references were
incomplete for P001/P007 — so the queue is treated as *discovery*, not
citation-coverage evidence.

## Phase 2 - Title/abstract screening (2026-07-22): 560/560 decided

The 560-paper queue was screened under a human-authorized AI protocol
(`AI_SCREENING_V1`), in batches B001-B029. The repository was first cleaned and
normalized (the malformed 58-column decisions table was migrated to an
append-only history + active snapshot; QA001 re-recorded rank 20's original
include as a superseding pair).

Batch flow (from `data/curated/screening/screening_batches.csv`):
B001-B003 migrated/reconstructed, B004-B011 native (ranks 61-220), B012-B029
native (ranks 221-560). Final counts: **260 include, 300 exclude, 0 unclear.**

Evidence: `data/curated/screening/title_abstract_decisions.csv` (560 active
rows), `title_abstract_decision_history.csv` (append-only),
`screening_batches.csv` (queue + row hashes per batch).

Two project decisions were logged here (in `docs/project/DECISION_LOG.md`):
adopt normalized event history, and freeze the screening queue until screening
completes.

## Phase 3 - Evidence-priority ranking: ordering the 260 inclusions

All 260 included papers received an evidence-priority score, and the ranking
was bridged into the legal full-text acquisition queue. The bridge had a
validation hardening pass (paper_id/canonical_paper_id added to RANKING_FIELDS;
24 queueing tests, 41 total) — commit `a4b14c7`.

Evidence: `outputs/fulltext_ranking/`, the ranking/queue bridge scripts, and
`tools/fulltext_pipeline/tests/`.

## Phase 4 - Lawful full-text acquisition and processing (2026-07-23 → 2026-08-07)

Full-text work proceeded in batches against the ranked queue, under the rule:
*acquire only legal open-access artifacts or lawfully obtained local copies,
never bypass paywalls.* Highlights, in order:

- **Batch 5 (ranks 81-100)**: 14 papers acquired/processed via Docling; two
  XML-only (Elsevier coredata), one PyMuPDF fallback, one (MuST-C, rank 91)
  imported from a user-supplied PDF.
- **Batch 6**: 5 auto-acquired + processed, then 10 more reviewed from
  user-supplied PDFs; 15/20 finalized as include, 5 paywalled ranks recorded
  unresolved FU1.
- **Batch 7**: 7 finalized include, 13 unresolved after lawful acquisition
  failed (403s, no_candidate, Elsevier coredata stubs).
- **Batch 8 bulk acquisition**: the 146 remaining undecided papers were queued
  and acquired up front; a retry pass with `--allow-unknown-rights --refresh`
  added more artifacts (22 with `rights_status=unknown`, honestly recorded).
- **Manual PDF import (2026-08-07)**: 76 user-supplied PDFs were identity-checked
  (sha256, first-page text, DOI/arXiv) and 70 imported (68 unique papers), 2
  flagged and skipped by user confirmation.
- **Batch 8 processing (2026-08-07)**: all 111 pending papers processed via
  Docling `--no-grobid`; the venv PATH bug was fixed, and a polluted registry
  was cleaned deterministically.

Throughout, source bytes stayed local and out of Git; PDF/XML/JATS/Docling were
kept as complementary representations, never overwriting the source artifact.

Evidence: `data/curated/fulltext/artifact_registry.csv` (300 artifact rows, 208
papers), `extraction_registry.csv` (252 rows), `fetch_attempt_registry.csv`
(476 lawful attempts), `outputs/fulltext/acquisition/FTA_*/`,
`outputs/manual_pdf_import_report_20260803.json`.

## Phase 5 - Full-text review and closure of the universe (2026-08-08)

- **Review batches 1-5**: 97 papers finalized; the first **exclude** decisions
  appeared (rank 448 not agriculture; rank 494 no CV / no dataset relevance).
- **13 stub-content failures** (12 Elsevier coredata stubs + 1 stub PDF) were
  re-acquired and confirmed unfillable, then recorded unresolved FU1.
- **Universe closed**: the last 36 undecided TA-included ranks were disposed.
  TomatoMAP (rank 184) was reviewed from its imported PDF → include_core,
  superseding a stale FU1; 8 ranks excluded as duplicates (FE05_DUPLICATE); 28
  recorded unresolved FU1.

**`full_text_decisions.csv` now has 262 rows → 260 active decisions: 150
include_core, 40 include_supporting, 60 unresolved, 10 exclude.** Every
TA-included paper has an active decision; no TA-included paper is undecided.

Evidence: `data/curated/screening/full_text_decisions.csv`,
`outputs/reconciliation_36_undecided.csv`. All reconciliation decisions are
AI-provisional pending human confirmation.

## Phase 6 - Method-gap matrix: the 190-paper re-run (2026-08-08)

The method-gap analysis — the heart of the "rigorously gated methodology study"
— was re-run over the full include universe. 190 papers (150 core + 40
supporting) were tagged across 6 dimensions (split rigor, baselines,
calibration, cross-sensor testing, code availability, dataset role) in 19
≤10-paper agent batches, then merged deterministically.

Headline: **calibration absent 189/190 (99.5%)**, same-sensor-only evaluation
129/190 (67.9%), no code 108/190 (56.8%), ≥4 simultaneous gaps **154/190
(81.1%)**. This became the project's quantitative case for sensor-aware,
calibration-conscious work.

Evidence: `outputs/method_gap_matrix.csv` (190 rows, 0 empty cells),
`outputs/mga_batch_1..19_*`. Prior 94-paper run archived at
`outputs/archive_method_gap_v1_20260803/`.

## Phase 7 - Evidence synthesis: registry, scores, claim ledger (2026-08-08)

- **Dataset registry**: 96 unique datasets, refreshed to the closed universe
  (2 name-duplicates merged; 3 lost merge victims re-scored from MGA evidence).
- **Opportunity scores**: all 96 datasets scored on 5 dimensions; ranks 1-96
  contiguous, every total = sum of its dimensions. Top: MuST-C 24.5, AgroVG
  22.0, MaizeField3D 21.5, OPPD 21.5.
- **Claim ledger**: extended to 32 entries (MGA-010, DSO-016..018, DT-006),
  then reconciled against the final scores — DSO-001/002/003/005 superseded
  (pre-refresh universes), DSO-019 recorded the final top-20 and the
  supersession rationale. Ledger: 33 rows.

Evidence: `outputs/dataset_registry.csv`, `outputs/dataset_opportunity_scores.csv`,
`data/curated/claim_ledger.csv`.

## Where we are now

The screening universe is closed and the synthesis layer is complete and
internally consistent (`screening_state validate` passes; coverage 260/260).
The research has a defensible quantitative gap story: **99.5% of the corpus
does not report calibration, 81% carry four or more simultaneous method gaps.**

Everything remains AI-provisional until human confirmation — especially the
final top-20 dataset selections and the supersession of DSO-001/002/003/005.
The next phase after confirmation is **experimental-design-gates** for the top
candidate datasets (e.g., MuST-C, MaizeField3D, OPPD, BonnBeetClouds3D).

## Recurring principles (visible in every phase)

- **Frozen-state rule**: never rebuild or re-rank frozen artifacts in place;
  create new versions and map by stable IDs.
- **Supersede, don't overwrite**: corrections are new events that point to what
  they replace (P004 edges, rank 20, TomatoMAP FU1, DSO-001/002/003/005).
- **Deterministic joins, bounded AI**: agents screen/tag/extract; Python
  finalizes, hashes, merges, and validates.
- **Lawful acquisition only**: no paywall bypass; `rights_status=unknown` is
  recorded honestly when access is unclear.
- **Claims need evidence locations**: no manuscript claim without a
  claim-ledger entry and an exact artifact location.
