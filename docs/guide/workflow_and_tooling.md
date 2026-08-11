# Workflow and tooling

How the research pipeline runs end to end, which tool drives each stage, and
the concrete numbers this project has produced at each stage (verified
2026-08-08 from the curated CSVs).

## Pipeline at a glance

```
snowball collection → title/abstract screening → evidence-priority ranking
→ lawful full-text acquisition → document processing → full-text review
→ method-gap analysis → evidence synthesis (datasets, scores, claims)
→ study protocol design
```

Each stage ends with a deterministic validation command before the next begins.

## Stage 1 — Snowball collection

Gather one-hop citations from seed dataset papers.

| Item | Value |
|---|---|
| Seeds | 13 identity-mapped papers |
| Provider relations in frozen accepted graph | 869 |
| Frozen output | `outputs/accepted_graph_2026-07-22/` |

Tooling: `tools/agri_cv_snowball_package/` collector.

```powershell
$env:OPENALEX_API_KEY = "..."; $env:OPENALEX_MAILTO = "..."; $env:S2_API_KEY = "..."
uv run python tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py `
  --input tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --out outputs/snowball_<purpose>_<YYYY-MM-DD> --providers both
```

Validation: `python scripts/research/audit_snowball_run.py`, then
`python scripts/research/build_accepted_graph.py`.

## Stage 2 — Title/abstract screening

Screen the frozen 560-candidate queue in batches of at most 20.

| Item | Value |
|---|---|
| Queue | 560 canonical candidates (frozen, rank-stable) |
| Decisions | 560 (260 include, 300 exclude) |
| Decision history | `data/curated/screening/title_abstract_decision_history.csv` (append-only) |
| Active snapshot | `title_abstract_decisions.csv` (never hand-edited) |

Tooling: `scripts/research/` + `/screen-paper` command + `paper-screener` agent.

```powershell
python scripts/research/screening_state.py validate --repo .
python scripts/research/prepare_screening_batch.py --repo . --ranks 61-80
# human/AI review of prepared workspace
python scripts/research/finalize_screening_batch.py outputs/screening_batches/batch_004_ranks_61-80 --repo .
```

## Stage 3 — Evidence-priority ranking

Score the 260 included papers to decide which full texts to acquire first,
using the weights in `config/fulltext_ranking.toml`. This is a ranking of ROI,
not a change to screening decisions.

Tooling: `python scripts/research/fulltext_ranking.py`, `/rank-fulltext`,
`/bootstrap-ranking` (deterministic Monte Carlo sensitivity), `/score-priority`.
Outputs land in `outputs/fulltext_ranking/` and `data/curated/ranking/`.

## Stage 4 — Lawful full-text acquisition

Resolve legal candidates by exact identifiers and download PDF/XML only when
rights permit. No paywall bypass, no shadow libraries.

| Item | Value |
|---|---|
| Fetch attempts recorded | 476 |
| Artifact registry rows | 300 |
| Papers with any artifact | 208 |
| Undecided papers still without artifact | 36 |
| User-supplied PDFs imported (2026-08-07) | 70 (68 unique papers) |

Tooling: `agri-fulltext` CLI in `tools/fulltext_pipeline/`.

```powershell
# queue from undecided TA-included papers
agri-fulltext queue --ranking outputs/fulltext_ranking/pending_146_fulltext.csv --out <queue.csv>
# resolve and download (local-only venv: prepend tools/fulltext_pipeline/.venv/Scripts to PATH)
agri-fulltext acquire <queue.csv> --artifact-set both
# register a lawfully obtained local copy
agri-fulltext import <file.pdf> --rank <N> --rights-status local_research_only
agri-fulltext validate
```

Registries updated: `artifact_registry.csv`, `fetch_attempt_registry.csv`,
`resolver_error_registry.csv`. Bytes stored under `data/raw/fulltext/` (ignored
by Git).

## Stage 5 — Document processing (Docling/GROBID/XML)

Normalize PDF/XML into layout-aware representations (JSON, HTML, Markdown,
chunk JSONL, extracted images/tables/formulas) without replacing the source.

| Item | Value |
|---|---|
| Extraction registry rows | 252 (208 papers) |
| QA: manual_review | 188 |
| QA: needs_review | 18 |
| QA: fail | 46 |

Tooling: `agri-fulltext process` with `--no-grobid`/`--no-docling` switches;
GROBID via Docker; Docling runs in `outputs/fulltext/processing/FTP_*`.

```powershell
agri-fulltext process --ranks 28 --no-grobid --refresh
agri-fulltext preflight <paper.pdf>
agri-fulltext render-pages <paper.pdf> --pages 2-4 --out <dir> --dpi 160
```

Windows note: on win32 the pipeline passes a `\\?\`-prefixed Docling output path
to stay under the 260-char MAX_PATH limit (fixed in `processing.py`).

## Stage 6 — Full-text review and finalization

Read the processed representations (JSON/Markdown + rendered pages) and issue a
source-located eligibility decision.

| Item | Value |
|---|---|
| Decision rows | 262 (260 active; 2 superseded pairs for rank 1 and rank 184) |
| include_core (active) | 150 |
| include_supporting (active) | 40 |
| unresolved (FU1 full text unavailable, active) | 60 |
| exclude (active) | 10 (8 FE05_DUPLICATE + 448 + 494) |
| Coverage | 260/260 TA-included papers decided (universe closed) |
| Review workspaces | `outputs/fulltext/reviews/review_*` |

Tooling: `agri-fulltext review-queue`, `prepare-review`, `finalize-review`;
`fulltext-reviewer` agent; `/review-fulltext`. Decisions land in
`data/curated/screening/full_text_decisions.csv` (never hand-edited).

```powershell
agri-fulltext review-queue --out outputs/fulltext/review_queue_b8/fulltext_review_queue.csv
agri-fulltext prepare-review <rank-or-paper-id> --out outputs/fulltext/reviews/review_<id>
# reviewer reads the workspace and writes a decision CSV
agri-fulltext finalize-review outputs/fulltext/reviews/review_<id>/decision.csv
```

Known pitfall: `finalize-review` fails on trailing-comma or unescaped commas in
`notes`; repair deterministically before finalizing.

## Stage 7 — Method-gap analysis

For included full-text papers, tag six dimensions: split rigor, baseline
strength, calibration reporting, cross-sensor testing, code availability, and
dataset role.

| Item | Value |
|---|---|
| Papers in method-gap matrix | 190 (0 empty cells) |
| Dimensions | 6 (split, baselines, calibration, cross-sensor, code, dataset role) |
| Example finding | calibration absent 189/190 (99.5%); ≥4 gaps 154/190 (81.1%) |

Tooling: `scripts/research/method_gap_*.py` + method-gap-analysis skill.

```powershell
python scripts/research/method_gap_extract_structured.py --repo .
python scripts/research/method_gap_evidence.py --repo .
# split outputs/method_gap_evidence.csv into <=10-paper batches, tag each with an agent
python scripts/research/method_gap_merge.py --repo . --batch-csvs outputs/mga_batch_*_results.csv
```

## Stage 8 — Evidence synthesis

Convert reviewed evidence into the dataset registry, opportunity scores, and
claim ledger. This is where datasets get ranked — never from citation counts
alone, only after actual experimental use and access are verified.

| Item | Value |
|---|---|
| Datasets in registry | 96 |
| Datasets scored (5 dims) | 96 |
| Claim-ledger entries | 32 |
| Top-scored dataset | MuST-C at 24.5/25 |

Tooling: `evidence-synthesizer` agent + skills
(dataset-opportunity-ranking, claim-ledger, paper-evidence-extraction).

## Stage 9 — Study-protocol design

Once dataset selection is human-confirmed, design a minimal falsifiable
experiment with leakage controls, strong simple baselines, grouped splits,
calibration, compute limits, and predeclared stop/go rules.

Tooling: `/design-study`, `experimental-design-gates` skill,
`methodology-strategist` agent.

## Tooling quick reference

| Tool | Where | Use it for |
|---|---|---|
| `scripts/research/*.py` | `scripts/research/` | Deterministic joins, hashes, counts, screening state, ranking, method-gap merging |
| `agri-fulltext` | `tools/fulltext_pipeline/` | Queueing, resolution, lawful acquisition, import, preflight, Docling/GROBID processing, review finalization |
| Snowball collector | `tools/agri_cv_snowball_package/` | One-hop citation gathering |
| OpenCode commands | `.opencode/commands/` (21) | `/screen-paper`, `/fulltext-status`, `/prepare-fulltext`, `/acquire-fulltext`, `/process-fulltext`, `/review-fulltext`, `/rank-datasets`, `/design-study`, ... |
| OpenCode skills | `.opencode/skills/` (14) | Bounded scientific procedures for each stage |
| OpenCode agents | `.opencode/agents/` | Bounded roles: screener, acquirer, processor, reviewer, synthesizer, auditor |
| Dashboard | `frontend/` | Visualize screening/ranking/full-text state |

## Commands to verify the numbers

```powershell
uv sync
uv run pytest
python scripts/research/screening_state.py validate --repo .
agri-fulltext status          # acquisition/processing summary
agri-fulltext validate        # registry/hash integrity
```

Note: the pipeline intentionally prefers deterministic Python for anything that
joins, hashes, counts, or rebuilds state; models and agents are used only for
bounded semantic judgments and writing.
