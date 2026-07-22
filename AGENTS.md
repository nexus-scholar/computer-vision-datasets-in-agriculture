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

## Stop conditions

Stop and report when:

- identity, DOI, title, authors, or year conflict materially;
- a curated CSV is malformed or a batch hash fails;
- an edit would change raw or already-accepted evidence;
- a candidate already has an active decision without an explicit supersession event;
- the requested batch exceeds 20 papers;
- a full-text claim lacks a page, section, table, or figure location;
- an experiment lacks a falsifiable claim, grouped split, strong simple baseline, and stop/go rule.
