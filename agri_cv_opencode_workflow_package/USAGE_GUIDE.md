# How to use the OpenCode workflow

## Why the workflow is designed this way

Free and smaller models are useful when tasks are narrow, files are explicit, outputs have schemas, and deterministic scripts handle counting, joining, hashing, and deduplication. They are unreliable when asked to inspect hundreds of papers, repair metadata, redesign the repository, and write a literature review in one session.

This package separates work into:

- deterministic Python operations;
- bounded agent judgments;
- human approval gates;
- durable, readable artifacts.

## Daily operating pattern

1. Start OpenCode in the repository root.
2. Run `/status`.
3. Choose one task that can finish in the session.
4. Use one specialist agent, either through a command or `@agent-name`.
5. Require the agent to write results to a named file, not only chat.
6. Run verification scripts.
7. Run `/close-session` to update the handoff and decision log.
8. Review `git diff` before committing.

## Agent map

| Agent | Use it for | Do not use it for |
|---|---|---|
| `research-lead` | Planning, sequencing, delegation, quality-gate decisions | Bulk extraction or silent rewrites |
| `repo-auditor` | Read-only repository and data-flow audits | Implementing fixes |
| `bibliography-auditor` | Seed identity, provider conflicts, relation completeness, graph quality | Broad narrative reviews |
| `corpus-curator` | PDF-to-seed mapping, hashes, readable filename plan | Renaming or editing raw PDFs |
| `paper-screener` | One-paper or small-batch inclusion/exclusion and actual-use decisions | Autonomous screening of hundreds of rows |
| `evidence-synthesizer` | Dataset registry, gap matrix, opportunity scores, claim ledger | Inventing missing evidence |
| `methodology-strategist` | Falsifiable study protocol, baselines, splits, statistics, stop-go gates | Starting a complex architecture before baseline gates |
| `workflow-maintainer` | Scripts, tests, schemas, documentation, migrations | Scientific inclusion decisions |
| `reproducibility-reviewer` | Read-only milestone verification | Making repairs directly |

## Skills

Skills are loaded on demand. The package includes:

- `small-model-discipline`
- `bibliographic-resolution`
- `snowball-quality-audit`
- `local-corpus-integrity`
- `systematic-screening`
- `paper-evidence-extraction`
- `dataset-opportunity-ranking`
- `claim-ledger`
- `experimental-design-gates`
- `reproducible-research-runs`

Tell an agent explicitly to load the relevant skill when the task is high risk.

## Commands

- `/status` — current state, blockers, and next bounded action.
- `/audit-run PATH` — audit a generated snowball run.
- `/audit-corpus PATHS` — verify local PDFs against the seed manifest.
- `/repair-seeds IDS` — prepare and validate seed corrections and a targeted rerun.
- `/build-accepted-graph RUNS_AND_AUDIT` — select the newest exact accepted identity from historical/repair runs and omit incomplete pairs.
- `/prepare-screening PATH` — create a canonical screening queue.
- `/screen-paper ID_OR_PATH` — screen one paper and record evidence.
- `/rank-datasets` — update the opportunity matrix from curated evidence only.
- `/design-study TOPIC_OR_DATASET` — draft a falsifiable study protocol.
- `/verify-repo` — run tests and consistency checks.
- `/close-session` — write a handoff, decisions, and one next action.

## Model selection

No model is pinned in the project files. Refresh and inspect configured models from PowerShell:

```powershell
opencode models --refresh
```

Inside the TUI, use:

```text
/models
```

Select the model at session start and keep it for one bounded task. Do not hardcode a temporary free model ID in committed project configuration.

For weaker models:

- provide exact file paths;
- ask for one output schema;
- cap full-text work to one paper and title/abstract work to 10–20 rows;
- request a preview before edits;
- require `unknown` rather than inference;
- verify with scripts and human review;
- use a second pass or second model only for disagreements and high-impact records.

## Suggested model-role allocation

Use the cheapest capable model for mechanical semantic work and reserve the strongest available free/local model for decisions:

| Work | Model demand | Batch |
|---|---|---:|
| Repository status summary | low | one repository snapshot |
| Title/abstract screening | low–medium | 10–20 rows |
| Full-paper evidence extraction | medium | one paper |
| Seed identity conflict | medium–high | one to five seeds |
| Study design / novelty argument | high | one claim family |
| Code patch plus tests | medium–high | one bug |

Model output is a proposal. Human-reviewed curated files are the evidence source of truth.

## Session boundaries

Create a new session when switching between:

- code repair;
- bibliographic identity;
- corpus integrity;
- paper screening;
- evidence synthesis;
- experimental design.

Do not carry the full citation graph in context. Store results in CSV/Markdown and load only the relevant rows.

## Human review checkpoints

A human must approve:

- every seed-provider identity;
- every full-text inclusion/exclusion decision used in synthesis;
- every claim-ledger upgrade to `supported`;
- the primary dataset selection;
- the study protocol before experiments;
- any destructive file move, Git rewrite, or overwrite of reviewed evidence.
