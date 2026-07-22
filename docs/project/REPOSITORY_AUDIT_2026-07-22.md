# Repository audit and cleanup — 2026-07-22

## Executive verdict

The uploaded repository contained valid research progress, but its screening layer was not structurally trustworthy enough to continue in place. The cleanup preserves the scientific state—60 active title/abstract decisions, the repaired seed identities, the accepted graph, the frozen 560-paper queue, and all historical collection runs—while replacing malformed, duplicated, stale, or weakly traceable files with a normalized workflow.

The cleaned repository is suitable for continuing at ranks 61–80. It is **not yet suitable for dataset-opportunity claims or manuscript conclusions**, because title/abstract decisions remain provisional and the accepted citation graph has two known incomplete Semantic Scholar reference sets.

## Preserved research progress

| Evidence layer | Preserved state |
|---|---|
| Seed corpus | 13 PDFs, renamed to stable P001–P013 paths and verified by SHA-256 |
| Bibliographic decisions | P004 and P013 repairs retained; 26 seed/provider decision rows retained |
| Provider collection | July 5 full run, July 22 repair run, and July 22 S2 retry retained |
| Accepted graph | 869 provider relations retained as the frozen graph snapshot |
| Screening queue | 560 canonical candidates retained with the original rank order and queue hash |
| Active title/abstract screening | 60 decisions retained: 55 include, 5 exclude, 0 unclear |
| Decision history | 61 events retained, including the original rank-20 inclusion and its later exclusion as an explicit superseding event |
| Batch provenance | Three screening batches plus one QA correction represented by validated per-batch files and hashes |

No title/abstract decision was independently re-adjudicated during cleanup. Structural defects were repaired; scientific judgments remain the responsibility of the active screening protocol and later full-text review.

## Critical defects found and repaired

### 1. The active screening CSV was malformed

The uploaded `title_abstract_decisions.csv` declared 58 columns, but rank 20 contained two unquoted comma fragments. Python's CSV parser exposed them under the `None` key, so the file was not a valid rectangular evidence table.

**Repair:** the screening state is now split into:

- `title_abstract_decision_history.csv` — append-only events;
- `title_abstract_decisions.csv` — derived active state with a compact controlled schema;
- `title_abstract_relevance.csv` — derived wide relevance flags;
- `title_abstract_decisions_enriched.csv` — derived human-readable join with queue metadata.

All files are written atomically and validated against the frozen queue.

### 2. Rank 20 had been overwritten instead of superseded

The original batch-001 snapshot recorded rank 20 as included. The correction run directly replaced that decision with an exclusion in the main CSV, despite the stated append-only policy.

**Repair:** the original event `TA_R0020` is restored in history. The exclusion is recorded as `TA_R0020_QA1` with `supersedes_screening_id=TA_R0020`. The active state correctly resolves to the exclusion.

### 3. Batch 002 was missing its screened-row snapshot

The provenance table claimed the batch passed, but `outputs/screening_batches/batch_002_ranks_21-40/screened_rows.csv` did not exist.

**Repair:** the batch snapshot was reconstructed from the curated decisions and verified against the frozen queue. Its provenance is explicitly labeled `reconstructed_from_curated_snapshot`; it is not misrepresented as an original native artifact.

### 4. Batch 003's CSV had no header

The file contained 20 data rows, but a CSV reader interpreted the first paper as the header and returned only 19 records.

**Repair:** the 20-row batch was reconstructed with the controlled schema and verified against queue ranks 41–60. Its provenance is labeled `reconstructed_from_headerless_snapshot`.

### 5. Batch provenance was misleading

All original batch rows pointed to the same final active-decision hash rather than a true immutable batch output. The third batch ID was malformed as `3: 003`.

**Repair:** `screening_batches.csv` now contains stable IDs (`B001`, `B002`, `QA001`, `B003`), each linked to its own screened-row file and SHA-256 hash. Reconstructed artifacts are labeled honestly.

### 6. Existing validation reports were false positives

The correction agent reported structural success despite the malformed active CSV, missing batch file, headerless batch file, and inconsistent hashes.

**Repair:** deterministic validation now rejects excess CSV columns, missing or duplicate batch provenance, invalid IDs, wrong queue hashes, unsupported protocol versions, malformed timestamps, and implicit decision overwrites.

## Repository cleanup

### Removed from the active tree

- empty `.agents/` and `.codex/` directories;
- duplicated installed workflow source under `agri_cv_opencode_workflow_package/`;
- duplicate citation CSVs and obsolete `seed_papers_original.csv`;
- stale timestamped seed-manifest backup;
- obsolete Codex prompt and nested requirements file;
- nested environment launch behavior that conflicted with the root `uv` project;
- live API cache directories containing hundreds of generated JSON files;
- Python bytecode and test caches;
- stale root and project documentation.

### Moved or consolidated

- 13 PDFs moved from the mixed `datasets-papers-2026-07-03/` directory to `data/raw/seed_papers/Pxxx_<slug>.pdf`;
- a stable PDF manifest records title, DOI, original filename, path, size, hash, and identity status;
- 671 OpenAlex/Semantic Scholar cache files consolidated into one immutable archive with an entry-level hash manifest;
- the exact pre-cleanup screening artifacts consolidated into a small audit-only archive;
- generated outputs remain versioned and separate from curated decisions.

## Code and workflow improvements

The cleanup adds a deterministic screening workflow:

1. `prepare_screening_batch.py` creates a bounded batch of at most 20 unscreened ranks.
2. OpenCode writes only the prepared `screened_rows.csv`.
3. `finalize_screening_batch.py` validates identity fields and controlled values before modifying curated state.
4. `screening_state.py` derives active decisions, relevance flags, the enriched view, and status from append-only history.
5. `check_research_repo.py` verifies structure, hashes, archives, PDFs, duplicates, and screening consistency.

The `/screen-paper` command is now a short orchestration prompt rather than an 800-line instruction that asks a free model to edit a large master CSV directly.

## Remaining scientific and provenance limitations

These limitations were preserved rather than hidden:

1. The accepted graph's quality gate is false because Semantic Scholar backward references are incomplete for P001 (0/47) and P007 (0/65).
2. P003 and P004 remain unresolved in Semantic Scholar; their accepted OpenAlex identities are sufficient for the frozen queue.
3. The legacy seed-resolution table does not name a reviewer or review timestamp.
4. The 60 decisions are AI-screened and provisional.
5. Ten active decisions have medium confidence: ranks 12, 15, 20, 25, 26, 32, 39, 40, 56, and 59.
6. Seventeen included experimental/benchmark rows still have `named_datasets=unknown`.
7. No paper has yet passed a source-located full-text evidence gate.
8. The include rate is 91.7%; this is compatible with a recall-first screen but makes full-text exclusion essential.

## Validation performed

- 8 Python tests passed.
- Python compilation passed for `src/` and `scripts/`.
- Screening validation passed: 61 history events, 60 active decisions, 560 queue candidates.
- Repository checker passed with zero errors and zero warnings after transient build artifacts were removed.
- All 13 PDFs passed file-signature and `pdfinfo` checks.
- All 13 PDF hashes match the manifest.
- The 671-entry API archive passed ZIP integrity testing and archive-hash validation.
- The 15-entry pre-cleanup screening archive passed ZIP integrity testing and archive-hash validation.
- All 30 OpenCode agent, command, and skill frontmatter blocks parsed successfully.
- `opencode.json` parsed successfully.

## Git note

The uploaded ZIP did not contain `.git`, so the audit could not inspect commit `bdabbec` directly. The replacement script deliberately preserves the user's real local `.git` directory and does not commit automatically. The previous repository state remains recoverable through both Git and the replacement backup.

## Safe next action

```text
/screen-paper 61-80
```

Before and after the batch:

```powershell
python scripts/research/screening_state.py validate --repo .
python scripts/research/check_research_repo.py --repo .
```
