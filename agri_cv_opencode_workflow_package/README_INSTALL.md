# Agricultural CV OpenCode research workflow package

This is a non-destructive overlay for the current repository. It adds project-local OpenCode rules, agents, skills, commands, research templates, and deterministic quality-control scripts. It also includes two optional source patches.

## What it does

- Adds `AGENTS.md` and `opencode.json` for bounded, auditable OpenCode behavior.
- Adds focused agents for repository auditing, bibliography repair, screening, synthesis, maintenance, and reproducibility review.
- Adds reusable skills that encode the scientific workflow.
- Adds commands for common research operations.
- Adds deterministic scripts for snowball-run auditing, seed corrections, and screening-queue generation.
- Adds human-readable templates for screening, evidence extraction, opportunity scoring, decisions, and claims.
- Includes patches that fix the inventory path bug and prevent low-confidence seed matches from being snowballed.

It does not delete, rename, or move existing files.

## Install on Windows PowerShell

From the project root, use either the PowerShell wrapper or the explicit commands below. The wrapper installs the overlay and checks both patches without applying them unless requested.

```powershell
# Safe default: install overlay and validate patches.
path\to\agri_cv_opencode_workflow_package\install.ps1 -Repo .

# After reviewing the patch files, optionally apply them too.
path\to\agri_cv_opencode_workflow_package\install.ps1 -Repo . -ApplyPatches
```

Manual equivalent:

```powershell
# 1. Back up the project first.
Copy-Item -Recurse -Force . ..\Computer-Vision-Datasets-in-Agriculture-backup

# 2. Extract this package beside the repository, then run:
python path\to\agri_cv_opencode_workflow_package\install.py --repo .

# 3. Preview the optional source patches.
git apply --check path\to\agri_cv_opencode_workflow_package\patches\0001-fix-inventory-output-path.patch
git apply --check path\to\agri_cv_opencode_workflow_package\patches\0002-harden-snowball-collector.patch

# 4. Apply them after the checks pass.
git apply path\to\agri_cv_opencode_workflow_package\patches\0001-fix-inventory-output-path.patch
git apply path\to\agri_cv_opencode_workflow_package\patches\0002-harden-snowball-collector.patch
```

The installer creates backups only when a destination file already exists. Use `--force` to overwrite after reviewing the backup directory printed by the installer.

## First run after installation

```powershell
# Audit the existing full snowball run.
python scripts/research/audit_snowball_run.py `
  outputs/snowball_full_2026-07-05 `
  --out outputs/audits/snowball_full_2026-07-05

# Preview seed corrections for P004 and P013.
python scripts/research/apply_seed_corrections.py `
  --manifest tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --corrections config/seed_corrections.csv

# Apply corrections after reviewing the preview.
python scripts/research/apply_seed_corrections.py `
  --manifest tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --corrections config/seed_corrections.csv `
  --apply
```

Then configure API credentials in the current PowerShell session:

```powershell
$env:OPENALEX_API_KEY = "your_openalex_key"
$env:OPENALEX_MAILTO = "your.email@example.com"
$env:S2_API_KEY = "your_semantic_scholar_key"
```

Run a repair collection in a new directory rather than overwriting the old run:

```powershell
uv run python tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py `
  --input tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --out outputs/snowball_repair_2026-07-22 `
  --providers both `
  --openalex-api-key "$env:OPENALEX_API_KEY" `
  --mailto "$env:OPENALEX_MAILTO" `
  --s2-api-key "$env:S2_API_KEY" `
  --seed-ids "P001,P003,P004,P005,P007,P012,P013"
```

Audit that repair run before combining it with any older results. Create the reviewed seed-audit file from the template, then complete one row for each seed/provider decision:

```powershell
Copy-Item `
  data/curated/templates/seed_resolution_audit.csv `
  data/curated/bibliography/seed_resolution_audit.csv
```

After manually completing `data/curated/bibliography/seed_resolution_audit.csv`, build a provenance-preserving accepted graph:

```powershell
python scripts/research/build_accepted_graph.py `
  --runs outputs/snowball_full_2026-07-05 outputs/snowball_repair_2026-07-22 `
  --seed-audit data/curated/bibliography/seed_resolution_audit.csv `
  --out outputs/accepted_graph_2026-07-22
```

Then create a generated screening queue:

```powershell
python scripts/research/prepare_screening_queue.py `
  outputs/accepted_graph_2026-07-22/accepted_snowball_edges.csv `
  --out outputs/screening_queue_2026-07-22
```

Do not move blank model-generated decisions into `data/curated/`; only reviewed decisions belong there.

## OpenCode setup

Start OpenCode from the repository root so it discovers:

- `AGENTS.md`
- `opencode.json`
- `.opencode/agents/`
- `.opencode/skills/`
- `.opencode/commands/`

No model IDs are hardcoded. Run `opencode models --refresh`, then select a model with `/models` in the TUI. Project subagents inherit the invoking primary agent's model unless you explicitly override one.

Begin with:

```text
/status
```

Then use:

```text
/audit-run outputs/snowball_full_2026-07-05
/audit-corpus datasets-papers-2026-07-03 tools/agri_cv_snowball_package/input/seed_papers_manifest.csv
/repair-seeds P004,P013
/build-accepted-graph outputs/snowball_full_2026-07-05 outputs/snowball_repair_2026-07-22 data/curated/bibliography/seed_resolution_audit.csv
/prepare-screening outputs/accepted_graph_2026-07-22/accepted_snowball_edges.csv
/screen-paper P010
/rank-datasets
/design-study WeedsGalore-or-selected-primary-dataset
/close-session
```

Read `START_HERE.md`, `USAGE_GUIDE.md`, and `MIGRATION_PLAN.md` before restructuring folders.

## Validation

See `VALIDATION_REPORT.md` for the checks performed against the supplied repository snapshot.
