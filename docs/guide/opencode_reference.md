# OpenCode reference: agents, commands, skills, and their scripts

Everything under `.opencode/`, what it does, and which Python scripts (in
`scripts/research/`, `src/`, or the `agri-fulltext` CLI under
`tools/fulltext_pipeline/`) each one drives.

## Directory layout

| Directory | Contents | Count |
|---|---|---|
| `.opencode/agents/` | Bounded agent definitions (markdown, YAML frontmatter with permissions) | 13 |
| `.opencode/commands/` | Thin repeatable commands invoked as `/command` | 22 |
| `.opencode/skills/` | Reusable scientific procedures, one folder per skill (`SKILL.md`) | 14 |
| `.opencode/node_modules/` | Local tooling dependencies, not project source | — |

How the layers fit together:

- A **command** (`/screen-paper`, `/acquire-fulltext`, ...) is the entry point.
- Each command declares an **agent** that executes it (`paper-screener`,
  `fulltext-acquirer`, ...).
- The agent loads the **skills** it is allowed to use
  (`systematic-screening`, `legal-fulltext-acquisition`, ...).
- The agent calls the deterministic **Python scripts** that own joins, hashes,
  counts, and registry updates. Agents never hand-edit decision CSVs.

## Agents (`.opencode/agents/`)

All subagents are read-only over curated evidence except where explicitly noted;
each carries a `steps` budget and a temperature. The permissions block in each
file is the authoritative list of allowed commands — the table below summarizes
the Python scripts each agent is wired to run.

| Agent | Role | Allowed Python / CLI scripts |
|---|---|---|
| `bibliography-auditor` | Validates seed identities, provider matches, citation relations, completeness, canonical dedup before screening | `scripts/research/audit_snowball_run.py`, `scripts/research/prepare_screening_queue.py`, `git diff` |
| `corpus-curator` | Audits local PDF corpus; maps files to seed IDs, verifies titles/hashes, proposes renames without touching bytes | `python -m agri_cv_novelty.inventory` (i.e. `src/agri_cv_novelty/inventory.py`), `pdfinfo`, `pdftotext` |
| `document-processor` | Preflight + bounded Docling/GROBID processing; prepares extraction QA artifacts | `agri-fulltext preflight/process/render-pages` via `uv run --project tools/fulltext_pipeline [--extra docling]`; `docker compose -f docker-compose.fulltext.yml` |
| `evidence-ranker` | Bounded evidence-priority scoring; runs deterministic bootstrap/sensitivity/diversity/evaluation; never changes screening decisions | `scripts/research/fulltext_ranking.py` (`bootstrap`, `prepare`, `finalize-batch`, `build`, `status`, `evaluate`) |
| `evidence-synthesizer` | Converts reviewed evidence into dataset registries, method-gap matrices, opportunity scores, claim-ledger entries | `scripts/research/*` (e.g. `method_gap_extract_structured.py`, `method_gap_evidence.py`, `method_gap_merge.py`) |
| `fulltext-acquirer` | Prepares bounded queues, resolves legal candidates, runs audited acquisition, reports unresolved works | `agri-fulltext queue/resolve/acquire/import` via `uv run --project tools/fulltext_pipeline` |
| `fulltext-reviewer` | Reviews one processed paper for eligibility and source-located dataset evidence | `agri-fulltext prepare-review`, `finalize-review`, `render-pages`, `validate` |
| `methodology-strategist` | Turns accepted evidence into a falsifiable, resource-aware study protocol | none (writes into `docs/project/` and `data/curated/` only after review) |
| `paper-screener` | Screens one prepared title/abstract batch or one full paper; deterministic finalization | `scripts/research/screening_state.py`, `prepare_screening_batch.py`, `finalize_screening_batch.py`, `check_research_repo.py`; `pdftotext`, `pdfinfo` |
| `repo-auditor` | Read-only audit of structure, lineage, duplication, tests, config, reproducibility | `scripts/research/audit_snowball_run.py`, `git status/diff/log` |
| `reproducibility-reviewer` | Final read-only gate: manifests, hashes, lineage, tests, readiness to synthesize/publish | `uv run pytest`, `scripts/research/audit_snowball_run.py`, `git status/diff` |
| `research-lead` | Primary orchestrator; picks the next bounded task, delegates to specialists, enforces quality gates | `scripts/research/audit_snowball_run.py`, `git status/diff` |
| `workflow-maintainer` | Maintains scripts, schemas, tests, docs, and workflow files without scientific decisions | `uv run pytest` / `python -m pytest`; never `git push`, never `git reset --hard` |

## Commands (`.opencode/commands/`)

Each command maps to a Python script or CLI subcommand; "—" means the command is
a read/write workflow over documents and curated data with no bespoke script.

| Command | Delegated agent | Python script / CLI it runs |
|---|---|---|
| `/acquire-fulltext` | fulltext-acquirer | `agri-fulltext acquire <queue.csv> --artifact-set both` |
| `/audit-corpus` | corpus-curator | `python -m agri_cv_novelty.inventory` (plus `pdfinfo`/`pdftotext`) |
| `/audit-run` | bibliography-auditor | `scripts/research/audit_snowball_run.py` |
| `/bootstrap-ranking` | evidence-ranker | `scripts/research/fulltext_ranking.py bootstrap` |
| `/build-accepted-graph` | workflow-maintainer | `scripts/research/build_accepted_graph.py` (previewed, oldest→newest runs) |
| `/close-session` | research-lead | — (writes `docs/project/SESSION_HANDOFF.md`, `DECISION_LOG.md`) |
| `/design-study` | methodology-strategist | — (drafts protocol from curated evidence) |
| `/evaluate-ranking` | reproducibility-reviewer | `scripts/research/fulltext_ranking.py evaluate` |
| `/fulltext-status` | fulltext-acquirer | `agri-fulltext status`; `agri-fulltext validate` |
| `/prepare-fulltext` | fulltext-acquirer | `agri-fulltext queue` (modes: `--ranking`, `--ranks`, or default) then `resolve` |
| `/prepare-priority` | evidence-ranker | `scripts/research/fulltext_ranking.py prepare --range` |
| `/prepare-screening` | workflow-maintainer | `scripts/research/prepare_screening_queue.py` |
| `/process-fulltext` | document-processor | `agri-fulltext process --ranks <range>` (with `--extra docling`) |
| `/rank-datasets` | evidence-synthesizer | — (updates dataset opportunity matrix from curated evidence) |
| `/rank-fulltext` | evidence-ranker | `scripts/research/fulltext_ranking.py build` |
| `/ranking-status` | evidence-ranker | `scripts/research/fulltext_ranking.py status` |
| `/repair-seeds` | bibliography-auditor | — (reads `config/seed_corrections.csv`, produces repair plan) |
| `/review-fulltext` | fulltext-reviewer | `agri-fulltext prepare-review <id>`; `agri-fulltext finalize-review <decision.csv>` |
| `/score-priority` | evidence-ranker | `scripts/research/fulltext_ranking.py finalize-batch`; then `... build` |
| `/screen-paper` | paper-screener | `scripts/research/screening_state.py validate`, `prepare_screening_batch.py`, `finalize_screening_batch.py`, `check_research_repo.py` |
| `/status` | research-lead | — (reads state docs + `git status`, reports blockers) |
| `/verify-repo` | reproducibility-reviewer | `uv run pytest` + audits; returns pass/conditional-pass/fail |

## Skills (`.opencode/skills/`)

Each skill is a single `SKILL.md` procedure. Several reference specific Python
scripts; those without a script are methodology procedures whose outputs live in
`data/curated/` or `docs/`.

| Skill | Purpose | Associated Python scripts |
|---|---|---|
| `bibliographic-resolution` | Validate paper identity (DOI/arXiv/PMID/title/year/authors) before collecting citation relations; five decision tiers (accepted → rejected/unresolved) | none directly (consumed by bibliography-auditor; inputs from `config/seed_corrections.csv`, provider caches) |
| `claim-ledger` | Maintain auditable claims with evidence IDs, locations, contradictions, uncertainty, statuses | none (writes `data/curated/claim_ledger.csv`) |
| `dataset-opportunity-ranking` | Rank datasets on 5 evidence-based dimensions; never citation count alone | none (evidence-synthesizer writes `outputs/dataset_opportunity_scores.csv`) |
| `experimental-design-gates` | Turn evidence into a falsifiable protocol with leakage controls, baselines, stop-go gates | none (protocol documents) |
| `fulltext-evidence-prioritization` | Two-stage paper scheduling (deterministic bootstrap + bounded AI scores) before acquisition; never a second eligibility screen | `scripts/research/fulltext_ranking.py` (all subcommands) |
| `legal-fulltext-acquisition` | Identifier-driven lawful acquisition; rights audit; no paywall/shadow-library access | `agri-fulltext` CLI (implemented in `tools/fulltext_pipeline/src/agri_fulltext/acquisition.py`, `resolvers.py`, `http_client.py`) |
| `local-corpus-integrity` | Map each local PDF to its seed via hash + first-page metadata; non-destructive filename plan | `src/agri_cv_novelty/inventory.py` (`python -m agri_cv_novelty.inventory`) |
| `method-gap-analysis` | Tag included papers on 6 dimensions (split rigor, baselines, calibration, cross-sensor, code, dataset role) | `scripts/research/method_gap_extract_structured.py`, `method_gap_evidence.py`, `method_gap_merge.py` |
| `paper-evidence-extraction` | Extract source-located manuscript-grade evidence from one paper | none directly (works inside `agri-fulltext prepare-review` workspaces: `llm/paper.md`, `llm/chunks.jsonl`) |
| `reproducible-research-runs` | Immutable auditable runs: manifests, input hashes, env, credentials-as-booleans, counts, verification | none (methodology; checked by reproducibility-reviewer) |
| `scholarly-pdf-normalization` | Maintain the representation stack (PDF/JATS/Docling JSON+HTML/GROBID TEI/Markdown/chunks) with page grounding | `agri-fulltext process` (implemented in `tools/fulltext_pipeline/src/agri_fulltext/processing.py`, `preflight.py`, `xml_extract.py`) |
| `small-model-discipline` | Keep smaller/free models reliable: task contract, batch limits, `unknown` fallback, verification | none (applies to all model-driven tasks) |
| `snowball-quality-audit` | Audit provider runs for low-confidence seeds, shortfalls, duplicates, conflicts, provenance | `scripts/research/audit_snowball_run.py` |
| `systematic-screening` | Controlled title/abstract and full-text protocol; separates citations, mentions, and actual use | `scripts/research/screening_state.py`, `prepare_screening_batch.py`, `finalize_screening_batch.py` |

## Script owners (reverse index)

The deterministic scripts and their consuming agents/commands:

- `scripts/research/fulltext_ranking.py` (subcommands `bootstrap`, `prepare`,
  `finalize-batch`, `build`, `status`, `evaluate`) — evidence-ranker;
  `/bootstrap-ranking`, `/prepare-priority`, `/score-priority`, `/rank-fulltext`,
  `/ranking-status`, `/evaluate-ranking`.
- `scripts/research/screening_state.py`, `prepare_screening_batch.py`,
  `finalize_screening_batch.py` — paper-screener; `/screen-paper`.
- `scripts/research/audit_snowball_run.py` — bibliography-auditor, repo-auditor,
  reproducibility-reviewer; `/audit-run`.
- `scripts/research/prepare_screening_queue.py` — bibliography-auditor,
  workflow-maintainer; `/prepare-screening`.
- `scripts/research/build_accepted_graph.py` — workflow-maintainer;
  `/build-accepted-graph`.
- `scripts/research/method_gap_*.py` — evidence-synthesizer (per
  `method-gap-analysis` skill).
- `src/agri_cv_novelty/inventory.py` — corpus-curator; `/audit-corpus`.
- `agri-fulltext` CLI (`tools/fulltext_pipeline/src/agri_fulltext/*.py`) —
  fulltext-acquirer, document-processor, fulltext-reviewer;
  `/acquire-fulltext`, `/prepare-fulltext`, `/process-fulltext`,
  `/review-fulltext`, `/fulltext-status`.
