# OpenAlex + Semantic Scholar one-hop snowball collector

This tool resolves the 13 controlled agricultural-CV seed papers and collects their backward references and forward citations from OpenAlex and Semantic Scholar.

Use the repository root `uv` environment. Do not create a nested virtual environment and do not write into an existing run directory.

## Controlled input

```text
input/seed_papers_manifest.csv
```

P002, P004, P010, and P013 contain repaired primary titles/identifiers. The canonical local PDFs and hashes are under `data/raw/seed_papers/`.

## Recommended run

From the repository root:

```powershell
$env:OPENALEX_API_KEY = "your_key"
$env:OPENALEX_MAILTO = "you@example.com"
$env:S2_API_KEY = "your_key"

uv run python tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py `
  --input tools/agri_cv_snowball_package/input/seed_papers_manifest.csv `
  --out outputs/snowball_<purpose>_<YYYY-MM-DD> `
  --providers both
```

Use `--seed-ids P001,P007` for a targeted retry. Use `--refresh-cache` only in a new output directory.

## Outputs

- provider and merged seed metadata;
- backward references;
- forward citations;
- combined edge and node tables;
- run summary and unresolved seeds;
- relation errors;
- run manifest;
- response cache and raw seed records.

Historical caches from the July 2026 runs are compressed under `data/raw/api_archives/`; the generated CSVs and raw seed records remain in their run directories.

Provider counts may differ. Never average them, and never treat a missing relation response as a true zero.
