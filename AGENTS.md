# Agricultural CV research workspace rules

## Mission

Build a defensible, reproducible research program around recent and underused agricultural computer-vision datasets, with special attention to segmentation, multimodal/spectral sensing, robustness, calibration, and sensor-aware reliability.

## Source-of-truth hierarchy

1. `data/curated/` contains explicit research decisions. Each table must state whether a row is AI-screened, human-confirmed, accepted, superseded, or unresolved.
2. `config/` and controlled seed manifests contain reviewed inputs and protocols.
3. Frozen queue/graph snapshots under `outputs/` define the current screening universe.
4. Other `outputs/` are generated artifacts and remain untrusted until audited.
5. `data/raw/`, local PDFs, provider-response archives, and source citation exports are immutable evidence.
6. Narrative documents must point to curated evidence rows or primary papers.

## Non-negotiable rules

- Never treat an ambiguous or low-confidence bibliographic match as resolved.
- Never infer actual dataset use from citation presence alone.
- Never overwrite a historical run or the frozen screening queue.
- Never hand-edit `title_abstract_decisions.csv`; update history through a validated batch or correction event.
- Never edit raw PDFs, provider records, archives, or source citation exports.
- Never write a manuscript claim without a claim-ledger entry and exact evidence location.
- Never use citation count alone as evidence of underutilization or dataset quality.
- Prefer deterministic Python for joins, hashes, IDs, counts, deduplication, state rebuilding, and validation.
- Use agents only for bounded semantic judgments, evidence extraction, and writing.

## AI-screening policy

The project owner authorizes autonomous AI title/abstract screening. These decisions are provisional. Human confirmation remains mandatory for:

- full-text inclusion central to the argument;
- actual dataset-use claims;
- access/license conclusions;
- dataset selection;
- manuscript claims;
- the final study protocol.

Use `unknown` or `unclear` when evidence is insufficient. Do not represent AI-only judgments as human-reviewed.

## Free-model discipline

- One bounded task per session.
- At most 20 title/abstract rows per batch.
- One paper per full-text evidence extraction.
- Read only the prepared batch input, the controlled protocol, and necessary local evidence.
- Write model output to a staging batch file; let deterministic scripts finalize it.
- End with validation, durable status, and one exact next action.

## Required screening commands

```powershell
python scripts/research/screening_state.py validate --repo .
python scripts/research/prepare_screening_batch.py --repo . --ranks 61-80
python scripts/research/finalize_screening_batch.py outputs/screening_batches/batch_004_ranks_61-80 --repo .
```

OpenCode should normally run these through `/screen-paper`.

## Required method-gap commands

After full-text decisions are finalized for a batch, run sequentially:

```powershell
python scripts/research/method_gap_extract_structured.py --repo .
python scripts/research/method_gap_evidence.py --repo .
# Then: split outputs/method_gap_evidence.csv into ≤10-paper batches,
#       tag each batch with an agent per the method-gap-analysis skill taxonomy,
#       writing each to outputs/mga_batch_{N}_results.csv
python scripts/research/method_gap_merge.py --repo . --batch-csvs outputs/mga_batch_*_results.csv
```

## Work state

### Completed
- Pipeline: queueing bridge implemented, 24 queueing tests / 41 total pass; committed `a4b14c7`, pushed `origin/master`
- Batch 1–3: 56 papers screened (40 core, 13 supporting, 2 unresolved)
- **Batch 5**: 14 full-text papers acquired/re-acquired via Docling, processed, and reviewed (ranks 81,83–100). Ranks 83,85 XML-only (Elsevier coredata). Rank 100 PDF required PyMuPDF fallback. Rank 91 (MuST-C) imported from user-supplied PDF, processed, reviewed.
- **Ranks 43,47,70,71**: previously failed extraction; user downloaded PDFs; imported, processed (Docling), and reviewed — rank 43 include_supporting (survey), 47 include_core (3D tomato stemwork, request-only data), 70 include_core (NIAM9weeds, HuggingFace), 71 include_supporting (INMATEH 3D tomato phenotyping)
- **Batch 6 (partial)**: 5 papers auto-acquired, processed, reviewed, finalized — rank 25 include_core (WeedsGalore U-Net), 29 include_supporting (edge-computing review), 30 include_core (Tianchi/GTPBD/Vaihingen HVM-UNet), 33 include_supporting (disease-detection review), 34 include_core (Pheno4D introduces, PLOS ONE)
- **Batch 6 (10 more, user PDFs)**: ranks 6,11,14,17,28,31,35,38,39,41 reviewed + finalized — 6 include_core FI01 (AgriAdapt dataset), 11 include_supporting FS01 (robotics review), 14 include_core FI02 (MFWD subset), 17 include_core FI02 (SoyCotton+CWD ES2-LeafSeg), 28 include_core FI01 (TomatoWUR introduced), 31 include_supporting FS01 (weed-control review), 35 include_core FI02 (Indian Pines/Pavia/KSC/SugarBeets/CWD), 38 include_core FI01 (Two-Season-WeedDet8 introduced), 39 include_core FI01 (Bean Soy UAV dataset), 41 include_core FI01 (3D Rice WBPH Damage, request-only)
- Full-text screening: **115 decisions** (69 core, 26 supporting, 20 unresolved, 0 excluded)
- Docling MAX_PATH bug fixed (rank 28, `biosystemseng`): docling image exports hit 261-char paths > Windows MAX_PATH (260), surfacing as FileNotFoundError inside `docling_core`. Fix in `_run_docling` (`processing.py`): on win32, pass a `\\?\`-prefixed `--output` when the worst-case `source_artifacts/image_000000_<64hex>.png` path exceeds 240 chars; added `_longpath_isfile` so asset traversal/copy preserves those files. Fixed rank 28: `FTP_20260802T135700Z`, docling=success, qa=manual_review (33 visual assets, 126 chunks, 6 tables). Run `process --ranks 28` with `--no-grobid`; all 41 tests pass.
- CLI bug: `finalize-review` crashes on trailing-comma CSV (AttributeError at `reviewing.py:104`); workaround: strip trailing comma before finalizing. Batch 7 also hit a variant: unescaped commas inside `notes`/`source_page` fields (22/27 body fields vs 20 header) → repaired deterministically via `_repair_b7_decisions.py` (reassembles split fields, re-quotes)
- **Batch 7**: queue built from `outputs/fulltext_ranking/batch7_next_20.csv` (ranks 52,62,78,103,105,106,109,114,117,139,145,149,150,155,184,188,212,268,278,334); `FTA_20260803T005806Z` acquired 8 (7 PDF + 1 XML-only); 7 Docling-success papers reviewed + finalized (139/149/150/212/268/334 include_core, 155 include_supporting FS01) with FTS ids `FTS_14de9157d8409d0cdb96`, `FTS_8e1e29cab85894959122`, `FTS_9ad93565f1aac789c53b`, `FTS_86107136ed60e764d9c2`, `FTS_fadce7ce4e7663da22ba`, `FTS_8f7b35f7cdb6938fce72`, `FTS_3d5cd1d204f78d501285`; 13 ranks (52,62,78,103,105,106,109,114,117,145,184,188,278) recorded unresolved (FU1_FULLTEXT_UNAVAILABLE, empty extraction_id) via `_record_unresolved_b7.py` after lawful acquisition failed (MDPI/Wiley/T&F 403, IEEE/IPK/figshare no_candidate, Elsevier coredata stub)
- Method-gap matrix: re-extracted — **94 papers** across 6 dimensions (up from 87; batch 7 added 7 via `mga_batch_11_results.csv`); all 94 tagged, 0 empty cells. Summary: calibration absent 86/94 (91.5%), same-sensor eval 64/94 (68.1%), no code 55/94 (58.5%), ≥4 gaps 67/94 (71%). Note: legacy tag vocabulary from batches 1-10 (e.g., available/public, multiple/strong_simple) is inconsistent with the batch-11 taxonomy.
- **Batch 6 complete**: 15/20 finalized as include; 5 paywalled ranks (13,23,26,32,40) recorded unresolved (FU1_FULLTEXT_UNAVAILABLE, empty extraction_id) via `_record_unresolved_5.py` after lawful acquisition attempts failed (13 Wiley 403; 23/26/32/40 IEEE no_candidate). FTS ids: `FTS_e8200c33a81dc42e4871`, `FTS_bf07ae30c5200c6c691d`, `FTS_2a62de017b4600a595b8`, `FTS_ed7c527d334232cf6fc2`, `FTS_f9493c5bc599494ab095`
- Evidence synthesis (initial pass): dataset registry (30 introduced datasets), opportunity scores (5 dims × 30 datasets), claim-ledger (9 entries)
  - Top datasets: AgroVG (22), PhenoBench (21), AgroTools (20.5), CropNet (20), LAST-Straw (20)

### Active
- **Dataset registry**: 51 datasets (+5 batch-7 introduced: Seedling RGB-depth DATA INRAE, Soybean MVSP2 point clouds, CottonWeedID15, CN20, GLDD)
- **Opportunity scores**: 51 scored; MuST-C tops at 24.5/25, Pheno4D 21.0 (rank 3), PhenoBench 21.0 (rank 4), Seedling RGB-depth 20.5 (rank 6), Soybean MVSP2 19.0 (rank 16), CN20 18.0 (rank 23), CottonWeedID15 16.0 (rank 29), GLDD 13.0 (rank 42)
- **Claim ledger**: 27 entries (+7 batch-7: DSO-011..DSO-015, MGA-009, DT-005)
- **Batch 8 (bulk acquisition before processing)**: workflow tweak — acquire the full 146 undecided TA-included papers up front, then batch-process later. Built 3 queues from `outputs/fulltext_ranking/pending_146_fulltext.csv` (146 papers sorted by recommended_fulltext_rank, chunks `pending_acq_{1,2,3}_of_3.csv`) via `agri-fulltext queue`; ran 3 acquisitions: `FTA_20260803T124948Z` (23), `FTA_20260803T130215Z` (24), `FTA_20260803T131505Z` (6) → **53 artifacts** (26 PDF, 27 XML; 12 papers got both), **41 papers newly covered** (138 with any artifact). Remaining 105/146 still lack a lawful artifact (PDF outcomes: 26 success / 34 failed / 72 no_candidate / 14 skipped_rights; XML: 27 success / 97 no_candidate / 21 skipped_rights / 1 failed)
- **Batch 8 retry pass (user-authorized)**: re-queued the 105 artifact-less papers (`pending_retry_{1,2,3}_of_3.csv`) and re-ran acquire with `--allow-unknown-rights --refresh` (`FTA_20260803T154719Z` 2, `FTA_20260803T155333Z` 19, `FTA_20260803T160244Z` 2) → **23 more artifacts** (4 PDF, 19 XML), 22 more papers covered (160 with any artifact). 22 artifacts recorded with `rights_status=unknown` (honest audit trail; no access control was bypassed — 403/no_candidate outcomes persist). 83/146 undecided papers still lack any artifact; `pending_processing=63`.
- **Batch 7 (20/20 disposed)**: 7 finalized include (ranks 139,149,150,155,212,268,334), 13 unresolved FU1 (ranks 52,62,78,103,105,106,109,114,117,145,184,188,278); manual resolution queue `outputs/fulltext/acquisition/FTA_20260803T005806Z/manual_resolution_queue.csv` reflects unfillable ranks
- **Manual PDF import (76 user-supplied PDFs, 2026-08-07)**: identities extracted to `outputs/manual_pdf_identities_20260803.json` (sha256, first-page text, DOI/arXiv); corpus-matched via `_pdf_match_v2.py` + manual verification of all 6 low-confidence matches. **70 imported** (`rights_status=local_research_only`, `version=user_supplied`, report `outputs/manual_pdf_import_report_20260803.json`), covering 68 unique papers (2 identical jae-54 PDFs → 1 registry row, duplicate artifact row removed; 1 FU1 paper TomatoMAP rank 184 re-covered from `s41597-026-06926-9_reference.pdf`). 4 files skipped as already-decided (ecoinform 2024, MFWD rank 1, `s41597-026-07092-8`, LAST-Straw). Corrected identities: `chong2023ral`→r207 RA-L 2023, `marks2022icra`→r257, `ECPA23`→r290, `2310.11516v2`→r192 (Field Robot RA-M), `s41597-025-06049-7`→r422 titleyear (Broad-Leaf Legumes), `j.smartag.SA202410032`→r528 titleyear, `cicba2017a`→r526, `1-s2.0-S2643651525001141`→r450 MaizeField3D (DataShare DOI). **2 flagged, not imported (user-confirmed skip 2026-08-07)**: `s41597-025-06513-4` (PlantSeg journal version; arXiv r2 EXCLUDED, zenodo dataset r245 included — article DOI not in corpus) and `s41597-026-07074-w` (3-year horticultural tomato SciData dataset not in corpus). Pipeline after import: 208 papers any artifact, 190 PDF, 287 artifact rows, `pending_processing=111`, `pending_acquisition=52`.
- 146 TA-included papers remain without a full-text decision; ~78 still lack a successfully acquired artifact. 111 papers (incl. 70 just-imported) await processing (`pending_processing=111`).
- All claim-ledger entries need human validation

## Stop conditions

Stop and report when:

- identity, DOI, title, authors, or year conflict materially;
- a curated CSV is malformed or a batch hash fails;
- an edit would change raw or already-accepted evidence;
- a candidate already has an active decision without an explicit supersession event;
- the requested batch exceeds 20 papers;
- a full-text claim lacks a page, section, table, or figure location;
- an experiment lacks a falsifiable claim, grouped split, strong simple baseline, and stop/go rule.

<!-- BEGIN AGRI-CV FULLTEXT WORKFLOW -->
## Full-text workflow rules

- Acquire only legal open-access artifacts or lawfully obtained local copies.
- Never bypass paywalls, login controls, CAPTCHAs, or use shadow libraries.
- Keep PDF/XML bytes local and out of Git unless redistribution rights are verified.
- Preserve original source bytes and SHA-256; derivatives never replace source artifacts.
- Treat publisher JATS, Docling JSON/HTML, GROBID TEI, Markdown, and JSONL chunks as complementary representations.
- Markdown and LLM chunks are navigation views, not evidentiary ground truth.
- Tables, figures, equations, diagrams, and page-sensitive claims require visual verification against the PDF or layout-aware representation.
- Full-text inclusion, actual dataset use, dataset selection, and manuscript claims remain explicit review decisions.
<!-- END AGRI-CV FULLTEXT WORKFLOW -->
