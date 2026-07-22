# Start here

This package turns the supplied repository from a useful prototype into a staged, auditable research workspace for OpenCode and free/local models.

## Current verdict

The repository has valuable assets: a locked Python environment, 13 readable PDFs, a one-hop OpenAlex/Semantic Scholar run, raw API records, and a small testable package. It is **not yet synthesis-ready** because one accepted seed identity is false, one provider relation fetch is incomplete, one seed manifest row is obsolete, generated and curated evidence are not separated, and Git has no usable baseline commit.

## The correct order

1. Protect the existing repository and create a real Git baseline.
2. Install the workflow overlay and apply the two reviewed patches.
3. Audit the historical run; retain it unchanged.
4. Repair P004 and P013 and rerun only affected/unresolved provider pairs.
5. Manually accept seed/provider identities in `seed_resolution_audit.csv`.
6. Build an accepted graph from historical and repair runs.
7. Create a canonical screening queue.
8. Screen titles/abstracts, then full text, with human approval.
9. Extract evidence into the dataset registry, method-gap matrix, and claim ledger.
10. Rank datasets and select one primary family.
11. Freeze a falsifiable study protocol.
12. Benchmark simple baselines before SARA-Lite or full SARA-Net.

## First commands

```powershell
# From the repository root after extracting this package beside it:
path\to\agri_cv_opencode_workflow_package\install.ps1 -Repo .

# Inspect and then apply the patches:
path\to\agri_cv_opencode_workflow_package\install.ps1 -Repo . -ApplyPatches

# Audit the historical run:
python scripts/research/audit_snowball_run.py `
  outputs/snowball_full_2026-07-05 `
  --out outputs/audits/snowball_full_2026-07-05
```

Then open OpenCode in the repository root and run:

```text
/status
```

## What to read

- `AUDIT_REPORT.md` — what is wrong and why it matters.
- `MIGRATION_PLAN.md` — phased research execution plan.
- `USAGE_GUIDE.md` — agents, skills, commands, and free-model discipline.
- `README_INSTALL.md` — installation and exact repair commands.
- `VALIDATION_REPORT.md` — tests performed on this package.

## Research principle

Generated metadata is not evidence. Citation presence is not dataset use. Agent output is not a human decision. Only accepted identities and reviewed evidence enter the curated layer or support manuscript claims.
