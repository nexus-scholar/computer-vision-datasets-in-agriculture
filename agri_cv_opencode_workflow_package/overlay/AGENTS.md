# Agricultural CV research workspace rules

## Mission

Build a defensible, reproducible research program around recent and underutilized agricultural computer-vision datasets, with special attention to segmentation, multimodal/spectral sensing, robustness, calibration, and sensor-aware reliability.

## Source-of-truth hierarchy

1. `data/curated/` contains human-reviewed evidence and decisions.
2. Seed manifests and `config/` contain controlled inputs.
3. `outputs/` contains generated artifacts and is not trusted until audited.
4. `data/raw/`, local PDFs, API cache, and raw provider JSON are immutable sources.
5. Narrative documents must point to curated evidence rows or primary papers.

## Non-negotiable rules

- Never treat `low_confidence`, ambiguous, or provider-disagreeing matches as resolved.
- Never snowball a seed until identity is accepted.
- Never overwrite an existing run directory; create a new dated run.
- Never edit raw PDFs, raw API JSON, or source citation exports.
- Never infer actual dataset use from citation presence alone.
- Never write a manuscript claim without a claim-ledger entry and evidence location.
- Never silently choose one provider when OpenAlex and Semantic Scholar disagree.
- Never perform destructive Git or filesystem commands without explicit approval.
- Prefer deterministic scripts for merging, counting, hashing, and deduplication.
- Use agents only for bounded semantic judgments and writing.

## Human-readable output

Every generated or curated artifact must include:

- purpose;
- input paths;
- creation date;
- method/version;
- status (`generated`, `reviewed`, `accepted`, `quarantined`);
- unresolved questions;
- next action.

Use stable IDs (`P001`, canonical paper keys, dataset IDs) in filenames and tables. Use explicit columns rather than encoded notes.

## Working method for free models

- One task per session.
- One paper at a time for full-text extraction.
- At most 10-20 rows per screening batch.
- Give exact input and output paths.
- Load only the skills needed for the task.
- Preview changes before writing.
- Stop and mark `unknown` when evidence is insufficient.
- End every session with a durable handoff.

## Required checks before synthesis

Read `@docs/workflow/QUALITY_GATES.md` and `@docs/project/CURRENT_STATE.md`.

For repository structure and commands, read `@docs/workflow/WORKFLOW.md` only when relevant.

## Common commands

```powershell
python scripts/research/audit_snowball_run.py <run-dir> --out <audit-dir>
python scripts/research/build_accepted_graph.py --runs <old-run> <repair-run> --seed-audit data/curated/bibliography/seed_resolution_audit.csv --out outputs/accepted_graph_<date>
python scripts/research/prepare_screening_queue.py <accepted-graph>/accepted_snowball_edges.csv --out outputs/screening_queue_<date>
python scripts/research/apply_seed_corrections.py --manifest <manifest.csv> --corrections config/seed_corrections.csv
python scripts/research/check_research_repo.py --repo .
uv run pytest
```

## Stop conditions

Stop and ask for human review when:

- a seed match is below the configured threshold;
- title, DOI, year, or authors conflict materially;
- downloaded relation counts are below provider-reported counts;
- a PDF identity does not match its manifest row;
- an edit would change raw or already-reviewed evidence;
- an inclusion decision depends on unavailable full text;
- a claim has no direct evidence location;
- a proposed experiment lacks a falsifiable primary claim, grouped split, or stop-go rule.
