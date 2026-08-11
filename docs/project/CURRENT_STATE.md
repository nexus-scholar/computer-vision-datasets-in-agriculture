# Current project state

Last reconciled: 2026-08-08

This file supersedes the 2026-07-22 version (kept in Git history) and reflects
the closed full-text universe and refreshed synthesis layer.

## Completed

### Discovery and screening

- Repository workflow and Git baseline established by the project owner.
- P004 false OpenAlex match repaired; historical P004 edges remain quarantined from the frozen accepted graph.
- OpenAlex/Semantic Scholar one-hop collection, repair run, and S2 retry preserved.
- Accepted graph snapshot built with 869 provider relations.
- Canonical screening queue frozen at 560 candidates.
- Title/abstract screening completed for all 560 candidates: 260 include, 300 exclude, 0 unclear (batches B001–B029, AI_SCREENING_V1).
- Rank 20 correction preserved as a superseding event rather than an in-place overwrite.
- Screening state migrated to a normalized and deterministically validated schema.

### Full-text layer

- Evidence-priority ranking completed for all 260 included papers and bridged into the lawful acquisition queue (queueing bridge hardened; 24 queueing tests / 41 total pass).
- Full-text screening universe **closed**: 260/260 TA-included papers have an active decision — 150 include_core, 40 include_supporting, 60 unresolved (FU1), 10 exclude (8 FE05_DUPLICATE + 448 + 494).
- 208 papers hold a lawful artifact (300 artifact rows); 208 have extraction rows (252 rows, QA: 188 manual_review / 18 needs_review / 46 fail).
- 476 lawful fetch attempts recorded; 70 user-supplied PDFs imported (68 unique papers).
- 13 content-level stub failures re-acquired and recorded unresolved.

### Synthesis layer

- Method-gap matrix re-run over the full 190-paper universe (6 dimensions, 0 empty cells). Headline: calibration absent 189/190 (99.5%); ≥4 simultaneous gaps 154/190 (81.1%).
- Dataset registry: 96 unique datasets; opportunity scores on 96 rows, ranks 1–96 contiguous, total = sum of dimensions.
- Claim ledger: 33 entries, reconciled against the closed-universe scores; DSO-001/002/003/005 superseded, DSO-019 records the final top-20.

See `docs/project/TIMELINE.md` for the phased narrative behind these bullets.

## Current blockers

1. All reconciliation and synthesis results are AI-provisional. Dataset selection and manuscript claims require human confirmation.
2. The final top-20 dataset selections (DSO-019) and the supersession of DSO-001/002/003/005 await human approval.
3. 60 active unresolved full-text decisions are recorded FU1 (unlawfully unfillable or stub content); they form a human-confirmation backlog, not acquisition targets.
4. The accepted graph was built with `allow_incomplete_relations=true` and S2 references remain incomplete for P001/P007; the frozen queue is discovery-only, not citation-coverage evidence.

## Frozen-state rule

Do not rebuild or re-rank frozen artifacts in place. Frozen in this state:
`outputs/screening_queue_2026-07-22/`, `outputs/accepted_graph_2026-07-22/`,
the `outputs/fulltext_ranking/` queues, the acquisition runs under
`outputs/fulltext/acquisition/FTA_*/`, and `outputs/reconciliation_36_undecided.csv`.
Corrections are new events that point to what they supersede; decisions map by
stable ID, not by rank.

## Exact next action

```text
Human: confirm the DSO-019 top-20 dataset selections (and supersession of
DSO-001/002/003/005), then run the experimental-design-gates phase for the top
candidate datasets (e.g., MuST-C, MaizeField3D, OPPD, BonnBeetClouds3D).
```

Before and after any screening change:

```powershell
python scripts/research/screening_state.py validate --repo .
```

## Downstream gate

Do not select final datasets or draft study protocols until the DSO-019
selections and supersessions are human-confirmed. Study-protocol design must
use source-located full-text evidence for actual dataset use, modality usage,
evaluation splits, robustness testing, and access/licensing.
