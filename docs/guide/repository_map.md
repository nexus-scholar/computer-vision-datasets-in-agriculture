# Repository map

Every top-level item in the workspace, what it contains, and what it is for.
This is a snapshot of the layout; small debug scripts appear and disappear, but
the architecture below is stable.

## Root files

| File | Purpose |
|---|---|
| `AGENTS.md` | Workspace rules loaded by OpenCode: source-of-truth hierarchy, AI-screening policy, required screening/method-gap commands, and the running work-state log |
| `README.md` | Project overview: current checkpoint, start-here commands, important paths, screening-state model |
| `PROJECT_INDEX.md` | Research question, active thesis, current phase, sources-of-truth table, immediate workflow |
| `pyproject.toml` | Root Python package `agri-cv-novelty` (fastapi, pandas, requests, uvicorn) + pytest config |
| `uv.lock` | Lockfile for the root `uv` environment (Python 3.12 per `.python-version`) |
| `opencode.json` | OpenCode configuration: permissions (read/edit/bash/task/webfetch all allowed), watcher ignores, per-agent permission blocks |
| `.gitignore` | Ignores venvs, `.env`, provider runs, PDF bytes; un-ignores the frozen queue/graph/audits/inventory so screening state stays committed |
| `.gitattributes` | Line-ending policy (LF for py/md/csv/json/toml, CRLF for ps1) |
| `.env.example`, `.env.fulltext.example` | Template env vars (OpenAlex/Semantic Scholar/Unpaywall keys, GROBID/Docling settings). Never commit real secrets |
| `docker-compose.fulltext.yml`, `docker-compose.fulltext.full.yml` | GROBID server containers used by full-text processing |
| `agri_cv_evidence_ranking_skill_package.zip`, `agri_cv_fulltext_workflow_package.zip` | Packaged skill bundles (staged, not yet imported) |
| `check_rank83.py`, `search_dataset.py`, `extract_dataset_info.py`, `temp_*.txt`, `temp_*.json`, `tmp_*.py` | Leftover ad-hoc debug scripts from past troubleshooting (rank 83/85 XML-only, PDF text scans). Scratch work, not part of the pipeline |

## Directories

### `.opencode/` — OpenCode control plane
- `skills/` — 14 reusable scientific procedures (bibliographic-resolution,
  systematic-screening, fulltext-evidence-prioritization, legal-fulltext-acquisition,
  local-corpus-integrity, scholarly-pdf-normalization, paper-evidence-extraction,
  method-gap-analysis, dataset-opportunity-ranking, claim-ledger,
  experimental-design-gates, reproducible-research-runs, small-model-discipline,
  snowball-quality-audit).
- `commands/` — 22 thin repeatable commands (`/screen-paper`, `/prepare-screening`,
  `/acquire-fulltext`, `/process-fulltext`, `/review-fulltext`, `/status`,
  `/rank-datasets`, `/design-study`, and more). Commands wrap the scripts and
  skills so sessions stay reproducible. See `docs/guide/opencode_reference.md`
  for a full breakdown of every command, agent, and skill.
- `agents/` — bounded specialist agent definitions (paper-screener,
  fulltext-acquirer, document-processor, fulltext-reviewer, evidence-synthesizer,
  repo-auditor, etc.).
- `node_modules/` — local tooling dependencies, not source.

### `config/` — Controlled inputs (reviewed, versioned)
- `screening_protocol_v1.md` — the controlled title/abstract screening protocol.
- `seed_corrections.csv` — reviewed seed identity corrections.
- `fulltext.toml` — acquisition source order, rights policy, Docling/GROBID
  processing settings, and paths to the full-text registries.
- `fulltext_ranking.toml` — versioned evidence-prioritization policy weights
  (science, feasibility, ROI, diversity, sensitivity).
- `README.md` — policy note: controlled inputs live here, never API keys.

### `data/` — Evidence
- `data/raw/` — immutable bytes.
  - `seed_papers/` — 13 identity-mapped seed PDFs plus SHA-256 manifest.
  - `citation_exports/` — report-derived citation tables.
  - `api_archives/` — compressed historical provider-response caches.
  - `fulltext/` — local lawful PDF/XML source bytes (208 paper folders; ignored by Git).
  - `migration_archives/` — exact pre-cleanup artifacts, audit only.
- `data/curated/` — explicit research decisions.
  - `bibliography/` — seed/provider identity decisions (`seed_resolution_audit.csv`).
  - `screening/` — `title_abstract_decision_history.csv` (append-only),
    `title_abstract_decisions.csv` (active 560-row snapshot),
    `title_abstract_relevance.csv` (derived tags),
    `title_abstract_decisions_enriched.csv` (regenerated join view),
    `screening_batches.csv` (batch provenance), `full_text_decisions.csv`
    (225 full-text decisions).
  - `fulltext/` — `artifact_registry.csv` (300 artifact rows),
    `fetch_attempt_registry.csv` (476 attempts),
    `resolver_error_registry.csv`, `extraction_registry.csv` (252 rows),
    `fulltext_quality_reviews.csv` (25 rows), `fulltext_acquisition_batches.csv`.
  - `ranking/` — `paper_priority_scores.csv` and batch/history provenance.
  - `claims/`, `datasets/`, `evidence/`, `protocols/`, `templates/` — intended
    homes for claim-ledger entries, dataset intelligence, evidence notes,
    approved protocols, and blank templates.
  - `claim_ledger.csv` — 27 claim entries with evidence locations.

### `docs/` — Narrative documentation
- `docs/project/` — state and history: `CURRENT_STATE.md`, `DECISION_LOG.md`,
  `CLAIM_LEDGER.md`, `SCREENING_STATS.md`, `SCREENING_STATUS.md`,
  `REPOSITORY_AUDIT_2026-07-22.md`, cleanup/migration docs, `SESSION_HANDOFF.md`.
- `docs/workflow/` — procedures: `WORKFLOW.md`, `FULLTEXT_WORKFLOW.md`,
  `PDF_REPRESENTATION_POLICY.md`, `FULLTEXT_PRIORITY_RANKING.md`,
  `FREE_MODEL_PROTOCOL.md`, `QUALITY_GATES.md`, `REPOSITORY_MAP.md`.
- `docs/guide/` — this guide (repository map + workflow/tooling reference).

### `outputs/` — Generated artifacts
- Committed frozen snapshots: `screening_queue_2026-07-22/` (560 ranks),
  `accepted_graph_2026-07-22/` (869 relations), `screening_batches/`,
  `audits/`, `inventory/`.
- Local (Git-ignored) runs: `snowball_*/`, `fulltext/` (acquisition runs
  `FTA_*`, processing runs `FTP_*`, review workspaces `review_*`,
  review-queue snapshots), `fulltext_ranking/` (scoring runs, bootstrap runs,
  `pending_146_fulltext.csv`, chunked acquisition queues).
- Synthesis artifacts: `dataset_registry.csv` (51 datasets),
  `dataset_opportunity_scores.csv` (51 scored), `method_gap_matrix.csv`
  (94 papers), `mga_batch_*` method-gap batches, `evidence_batch_*.csv`,
  `manual_pdf_*` import work (2026-08-07, 70 imported user-supplied PDFs).

### `scripts/research/` — Deterministic Python utilities
- Screening: `screening_state.py` (validate), `prepare_screening_batch.py`,
  `finalize_screening_batch.py`, `prepare_screening_queue.py`.
- Full text: `fulltext_ranking.py` (evidence-priority scoring, largest script),
  `method_gap_extract_structured.py`, `method_gap_evidence.py`,
  `method_gap_merge.py`.
- Maintenance: `audit_snowball_run.py`, `build_accepted_graph.py`,
  `apply_seed_corrections.py`, `check_research_repo.py`, plus one-off
  `_record_unresolved_b8.py`, `_cleanup_failed_docling_run.py`.

### `src/agri_cv_novelty/` — Root package
- `inventory.py` — repository/CSV inventory and SHA-256 hashing.
- `screening.py` — screening decision schema constants and validation.

### `tests/` — Pytest suite
- `test_inventory.py`, `test_screening_state.py`, `test_fulltext_ranking.py`,
  `test_workflow_scripts.py` under `tests/research/`.

### `tools/` — Isolated sub-packages
- `agri_cv_snowball_package/` — OpenAlex + Semantic Scholar one-hop snowball
  collector (`scripts/collect_openalex_semantic_scholar_snowball.py`, seed
  manifest input, run wrappers).
- `fulltext_pipeline/` — the `agri-fulltext` CLI with its own venv and
  `pyproject.toml`. Source modules in `src/agri_fulltext/` (acquisition,
  resolvers, http_client, preflight, processing, reviewing, queueing, state,
  xml_extract, config, models, schema, io_utils). ~50 scripts under `tests/`,
  mostly one-off `_check_*`/`_tmp_*` helpers plus real tests
  (`test_queueing.py`, `test_reviewing.py`, `test_preflight_import.py`, etc.).

### `frontend/` — Research dashboard
- HTMX + Tailwind + Vite single-page app over a FastAPI backend
  (`backend/main.py`, `backend/routes.py`, `backend/database.py`) visualizing
  screening data, priority scores, batch status, and full-text progress.
  Run with `uv run uvicorn frontend.backend.main:app --reload --port 8000`.

### Scratch/temporary
- `test_doc_single/`, `tmp_docling/` — Docling smoke-test scratch dirs
  (single-paper runs, logs, rendered page images). Temporary, uncommitted.
- `.venv/` — Git-ignored root Python virtual environment.
- `.git/` — Git history; current branch tracks the research pipeline commits.

## Trust levels

1. **Immutable evidence**: `data/raw/`, archives, provider responses.
2. **Reviewed inputs**: `config/`, `data/curated/` registries and decision tables.
3. **Frozen snapshots**: `outputs/screening_queue_2026-07-22/`,
   `outputs/accepted_graph_2026-07-22/`, `outputs/screening_batches/`.
4. **Generated (untrusted until audited)**: everything else under `outputs/`.

Rules: never hand-edit `title_abstract_decisions.csv` or `full_text_decisions.csv`
(update through validated batches); never overwrite a historical run; prefer
deterministic Python for joins, hashes, counts, and validation; use agents only
for bounded semantic judgments and writing.
