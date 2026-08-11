# Full-text review protocol

A reviewer-facing protocol for judging one processed full-text paper against
the agricultural-CV inclusion question, recording source-located evidence, and
finalizing the decision into the append-only full-text decision table.

> Status note (2026-08-08): the full-text screening universe is **closed**
> (260/260 TA-included papers have an active decision). This protocol documents
> the procedure used to reach that state and the procedure for any future
> re-review or correction event. **The DSO-019 dataset selections remain on
> hold** until human confirmation; this protocol governs eligibility and
> dataset-use recording, not dataset selection.

## Purpose

Title/abstract screening is discovery. Full-text review converts an `include`
into a source-located eligibility decision with an explicit answer to *"is a
dataset actually used, and how?"* The review must never infer actual dataset
use from citation presence, and must never promote an ambiguous or
low-confidence match to resolved.

## Where review happens

- Review workspace: `outputs/fulltext/reviews/review_<id>/` (one per paper),
  containing `review_context.json` (paths + extraction manifest hash),
  `review_manifest.json` (registry paths + hashes), and
  `decision_template.csv` (exactly one empty decision row).
- Evidence sources: `llm/paper.md`, `llm/chunks.jsonl` for navigation; the
  original PDF/publisher XML and `docling/normalized/document.{json,html}` as
  evidentiary ground truth; rendered pages on demand.
- Decision target: `data/curated/screening/full_text_decisions.csv`
  (append-only; **never hand-edited**).

## Preconditions before review

1. The paper has an extraction row with `qa_status` in
   `manual_review` / `needs_review`. A `fail` extraction must be reprocessed
   before review.
2. The extraction manifest SHA-256 in `review_context.json` matches the actual
   manifest.
3. One paper per review workspace, one workspace per paper.

## The decisions

| Decision | Meaning | Reason-code prefix |
|---|---|---|
| `include_core` | central to the research argument; introduces, uses, or benchmarks a relevant ag-CV dataset | `FI` |
| `include_supporting` | useful supporting method, review, or peripheral evidence | `FS` |
| `exclude` | outside the agricultural-CV scope | `FE` |
| `unresolved` | full text could not be lawfully obtained or is content-empty | `FU` |

The finalizer (`finalize_review` in `reviewing.py`) enforces the prefix —
`FI*` for core, `FS*` for supporting, `FE*` for exclude, `FU*` for unresolved —
and a reason code that does not match its decision's prefix is rejected.

## The controlled vocabulary

Reason codes are semicolon-separated (`;`) when a row maps to several. The
vocabulary below is the *intended* one. **Known debt:** the historical
`full_text_decisions.csv` contains legacy variants (e.g. `FI1`, `FI-01`,
`FI01_INTRODUCES_DATASET`, `FS01_RELEVANT_METHOD`) that predate this protocol.
New rows should use the canonical codes here; a normalization pass over the
historical table is a proposed maintenance task.

### Inclusion codes

- `FI01` introduces a new dataset
- `FI02` uses an existing dataset (training or evaluation)
- `FI04` benchmark / challenge / evaluation protocol
- `FI05` relevant agricultural-CV method
- `FI06` multimodal, spectral, depth, LiDAR, 3D, or temporal learning
- `FI07` robustness, domain shift, cross-sensor, missing/corrupted input
- `FI08` uncertainty, calibration, failure detection, selective prediction

### Supporting codes

- `FS01` relevant method, review, or survey
- `FS02` related dataset or resource catalog

### Exclusion codes

- `FE01_NOT_AGRICULTURE`
- `FE02_NO_COMPUTER_VISION`
- `FE03_NO_DATASET_RELEVANCE`
- `FE05_DUPLICATE` (must name the superseded twin in `notes`)

### Unresolved codes

- `FU1_FULLTEXT_UNAVAILABLE` (lawful acquisition failed: paywall 403,
  `no_candidate`, or content-empty stub; `extraction_id` empty)

## The dataset-relationship vocabulary

`dataset_relationship` (exactly one): `introduced`, `used_training`,
`used_evaluation`, `used_pretraining`, `extended`, `repackaged`,
`benchmarked`, `compared_descriptively`, `mentioned_only`, `unclear`.

Rules:

- `mentioned_only` when the paper cites/names a dataset without experimental
  use — a citation is not use.
- `introduced` only when the paper itself releases/describes the dataset.
- `unclear` when the evidence is insufficient; do not guess.

`actual_dataset_use`: `yes` / `no` / `unclear`. When `yes`, at least one of
`source_page` / `source_section` / `source_table` / `source_figure` must be
filled (the finalizer enforces this).

## Evidence and source-location rules

- Every substantive evidence item records page, section, table, figure, or
  appendix. Cite in `evidence_summary` the exact location, not the paragraph.
- Tables, figures, equations, diagrams, and page-order-sensitive claims must be
  checked against the PDF / Docling HTML/JSON or a rendered page — never from
  `llm/paper.md` alone.
- Separate observed facts, author claims, and reviewer inference in the summary.
- Do not quote long passages into the curated table.
- `named_datasets=unknown` is a valid result when use is plausible but the name
  is not stated; do not fill it with a guess.
- Full-text inclusion and actual dataset use remain reviewer decisions; they
  are never implied by extraction success.

## Human-confirmation gates

These are mandatory for humans, not delegable to models (from AGENTS.md):

1. full-text inclusion central to the argument;
2. actual dataset-use claims;
3. dataset selection (the DSO-019 list — **still on hold**);
4. access/license conclusions;
5. manuscript claims;
6. the final study protocol.

AI decisions are provisional; mark rows `reviewer=opencode_ai` and leave the
human gate to flip them to confirmed.

## Finalizing a decision

1. Fill `decision_template.csv` (one row) using proper CSV quoting — write via
   `csv.DictWriter` / `io_utils.atomic_write_csv`, **never by hand-editing with
   unescaped commas**. Known pitfall: a multi-`,`/`;` `notes` field written
   unquoted splits into extra columns and aborts the finalizer; repair
   deterministically before finalizing.
2. Run:
   ```powershell
   uv run --project tools/fulltext_pipeline agri-fulltext --repo . finalize-review `
     outputs/fulltext/reviews/review_<id>/decision.csv
   ```
3. The finalizer validates: schema match, exactly one row, identity fields match
   the active extraction, decision + prefix-consistent reason code,
   `actual_dataset_use` in {yes,no,unclear}, valid `dataset_relationship`,
   evidence summary present for includes, source locator present when use=yes,
   and an explicit supersession when a decision for that `paper_id` already
   exists.
4. On success it appends a new `FTS_*` row. The workspace decision CSV is the
   provenance record; the registry row is authoritative.

## Corrections and supersessions

- Never edit a historical decision in place. A correction is a **new row** whose
  `supersedes_fulltext_screening_id` names the exact earlier `FTS_*` id. The
  finalizer refuses a new decision for a paper that already has one unless the
  supersession is explicit.
- Example: TomatoMAP (rank 184) was reviewed from its imported PDF →
  `include_core` (`FTS_639cf9461904678ed830`) superseding the stale
  `FU1` (`FTS_b5e2c2ba51e32e54f383`).
- Duplicate exclusions (`FE05_DUPLICATE`) must name the retained twin's `FTS_*`
  id in `notes` (see `outputs/reconciliation_36_undecided.csv` for the batch-8
  map).

## Recording unresolved papers

When lawful acquisition failed (paywall 403, `no_candidate`, rights-unknown
without permission to proceed) or the artifact is a content-empty stub:

- Record `decision=unresolved`, `reason_code=FU1_FULLTEXT_UNAVAILABLE`, and an
  **empty** `extraction_id`.
- Do this through the deterministic scripts
  (`_record_unresolved_*.py`) — never by appending a bare row.
- Keep the honest `rights_status=unknown` audit trail; do not represent
  "could not fetch" as "prohibited".

## Verification after any batch

```powershell
uv run --project tools/fulltext_pipeline agri-fulltext --repo . validate
uv run --project tools/fulltext_pipeline agri-fulltext --repo . status
python scripts/research/screening_state.py validate --repo .
uv run pytest
```

After reconciliation/bulk events, re-verify universe closure:

- `python` coverage check: every TA-included paper (260) has exactly one active
  FT decision (join on active rows only — exclude superseded ones).

## Related documents

- `docs/workflow/FULLTEXT_WORKFLOW.md` — acquisition and processing that feeds review.
- `config/screening_protocol_v1.md` — title/abstract stage and controlled tags.
- `docs/project/TIMELINE.md` — phased history, including why the universe closed.
- `docs/project/CURRENT_STATE.md` — blockers and exact next action.
- AGENTS.md work-state log — per-batch dispositions and known pitfalls.
