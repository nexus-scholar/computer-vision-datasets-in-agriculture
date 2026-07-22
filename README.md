# Underutilized Agricultural CV Datasets

This repository is the local research workspace for the project on underutilized computer vision datasets in agriculture and novelty-oriented paper directions.

## Current Inputs

- Deep research report: `references/underutilized-agri-cv-datasets-deep-research-2026-07-03.md`
- Extracted citation CSVs: `data/raw/citation_exports/`
- Local full-text PDFs and duplicated citation exports: `datasets-papers-2026-07-03/`
- Reproducible OpenAlex + Semantic Scholar snowballing package: `tools/agri_cv_snowball_package/`

## Setup

```powershell
uv sync
uv run agri-cv-inventory
```

The inventory command is intentionally local-only. It counts citation rows, seed rows, PDFs, and can write a reproducibility manifest:

```powershell
uv run agri-cv-inventory --write-manifest outputs/inventory/local_file_manifest.csv
```

## Snowballing

The packaged snowball collector is preserved under `tools/agri_cv_snowball_package/`.

```powershell
cd tools/agri_cv_snowball_package
$env:OPENALEX_MAILTO = "your.email@example.com"
$env:S2_API_KEY = "your_semantic_scholar_api_key" # optional
uv run python scripts/collect_openalex_semantic_scholar_snowball.py `
  --input input/seed_papers_manifest.csv `
  --out outputs `
  --providers both
```

Use a smaller run first when checking API access:

```powershell
uv run python tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py `
  --input tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --out outputs/snowball_smoke `
  --providers both `
  --max-forward-citations 10 `
  --max-backward-references 10
```

## Notes

The report marks `P013 TomatoPGT ecosystem` as needing manual verification because the original citation row lacked reliable title/authors. Keep that caveat attached until it is resolved from a primary source.

