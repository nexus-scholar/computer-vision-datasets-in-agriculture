# Workspace Guide

This folder explains what the repository contains, how the research workflow
runs, and which tools drive it — using the current agricultural-CV research
program as the worked example. It is the on-ramp for anyone (or any agent) new
to the workspace.

## Files

| File | Contents |
|---|---|
| `repository_map.md` | Folder-by-folder and file-by-file explanation of the whole repo |
| `workflow_and_tooling.md` | End-to-end pipeline stages with concrete numbers, plus every command and tool used at each stage |
| `opencode_reference.md` | Every agent (13), command (22), and skill (14) under `.opencode/`, each with its associated Python scripts |
| `README.md` (this file) | Orientation and a dated snapshot of the current research state |

The full project history — from the 13 seed papers to the closed full-text
universe and the refreshed synthesis — is told narratively in
`docs/project/TIMELINE.md`. The reviewer-facing procedure for judging one
full-text paper (decision codes, source-location rules, finalization,
corrections) is in `docs/project/FULLTEXT_REVIEW_PROTOCOL.md`.

## Current research snapshot (verified 2026-08-08, after method-gap + synthesis finalization)

Numbers below were computed from the curated CSVs, not copied from memory.
Regenerate them anytime with the commands in `workflow_and_tooling.md`.

### Screening layer

| Metric | Value | Source |
|---|---|---|
| Seed papers (identity-mapped PDFs) | 13 | `data/raw/seed_papers/` |
| Provider citation relations in frozen graph | 869 | `outputs/accepted_graph_2026-07-22/` |
| Canonical candidates in frozen queue | 560 (ranks 1–560) | `outputs/screening_queue_2026-07-22/screening_queue.csv` |
| Title/abstract decisions | 560 total | `data/curated/screening/title_abstract_decisions.csv` |
| — include | 260 | |
| — exclude | 300 | |

### Full-text layer

| Metric | Value | Source |
|---|---|---|
| Full-text decision rows | 262 (2 superseded → **260 active**) | `data/curated/screening/full_text_decisions.csv` |
| — include_core (active) | 150 | |
| — include_supporting (active) | 40 | |
| — unresolved FU1 full text unavailable (active) | 60 | |
| — exclude (active) | 10 (8 FE05_DUPLICATE + 448 + 494) | |
| Screening-universe closure | 260/260 TA-included papers have an active FT decision (0 undecided) | join of TA decisions minus active FT decisions |
| Papers with any lawful artifact | 208 | `data/curated/fulltext/artifact_registry.csv` (300 artifact rows) |
| Papers with an extraction row | 208 | `data/curated/fulltext/extraction_registry.csv` (252 rows) |
| — manual_review QA | 188 | |
| — needs_review QA | 18 | |
| — fail QA | 46 | |
| Lawful fetch attempts recorded | 476 | `data/curated/fulltext/fetch_attempt_registry.csv` |
| Quality-review rows | 25 | `data/curated/fulltext/fulltext_quality_reviews.csv` |

The full-text screening universe is **closed**: no TA-included paper is
undecided, and every artifact-bearing paper has a decision. The 60 active
`unresolved` rows are papers that could not be lawfully acquired (FU1) or that
record the 13 stub-content failures; they are the human-confirmation backlog,
not acquisition targets.

### Synthesis layer

| Metric | Value | Source |
|---|---|---|
| Datasets in registry | 96 (closed-universe refresh) | `outputs/dataset_registry.csv` |
| Datasets with opportunity scores | 96 (ranks 1–96 contiguous; total = Σ dims) | `outputs/dataset_opportunity_scores.csv` |
| Papers in method-gap matrix | 190, all 6 dims, 0 empty cells | `outputs/method_gap_matrix.csv` |
| Method-gap headline | calibration absent 189/190 (99.5%); ≥4 gaps 154/190 (81.1%) | |
| Claim-ledger entries | 32 (+MGA-010, DSO-016..018, DT-006) | `data/curated/claim_ledger.csv` |

## How to use this guide

1. Read `repository_map.md` to learn where every kind of artifact lives and
   which layers are trusted evidence vs. generated output.
2. Read `opencode_reference.md` for the full breakdown of the agents, commands,
   and skills under `.opencode/`, and the Python scripts that back them.
3. Read `workflow_and_tooling.md` to run the pipeline (or understand a run that
   already happened), with the exact commands.
4. Treat the numbers above as a snapshot. If AGENTS.md and this guide disagree,
   prefer the values recomputed from the CSVs; update AGENTS.md's work-state log
   in the next maintenance pass.

## Rules that shape everything

- `data/raw/` and archived provider responses are immutable evidence.
- `data/curated/` holds explicit research decisions; every row states whether it
  is AI-screened, human-confirmed, accepted, superseded, or unresolved.
- `config/` holds reviewed protocols and controlled inputs.
- `outputs/` runs are immutable; the frozen queue and accepted graph are the
  only `outputs/` that are committed to Git.
- Full text is acquired only through legal, identifier-driven resolution; PDF/XML
  bytes stay local and out of Git unless redistribution rights are verified.
