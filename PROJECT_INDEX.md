# Project Index

## Research Question

Which recent or underutilized agricultural computer vision datasets offer credible research novelty for a first paper, and which benchmark directions are defensible from the available evidence?

## Evidence Folders

| Path | Purpose |
|---|---|
| `references/` | Preserved source report and project reference notes. |
| `data/raw/citation_exports/` | Citation CSVs extracted from the deep research report. |
| `datasets-papers-2026-07-03/` | Local PDFs and source files downloaded for the dataset papers. |
| `tools/agri_cv_snowball_package/` | Reproducible OpenAlex + Semantic Scholar snowballing scripts and seed manifests. |
| `src/agri_cv_novelty/` | Local Python utilities for inventory, audit, and future extraction workflows. |
| `outputs/` | Generated manifests, snowball outputs, and analysis tables. Ignored by git. |

## Immediate Workflow

1. Run `uv sync`.
2. Run `uv run agri-cv-inventory --write-manifest outputs/inventory/local_file_manifest.csv`.
3. Smoke-test the snowball collector with small forward/backward limits.
4. Resolve the report caveat for `P013 TomatoPGT ecosystem`.
5. Start a dataset-by-dataset evidence matrix from citation rows plus local PDFs.

