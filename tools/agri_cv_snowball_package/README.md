# Agriculture CV 13-paper OpenAlex + Semantic Scholar snowballing package

This package is prepared for the 13 agriculture computer-vision dataset papers from the earlier curated CSVs.
It resolves each seed paper in **OpenAlex** and **Semantic Scholar**, then collects one-hop backward and forward snowballing data:

- **Backward snowballing** = papers referenced by each seed paper.
- **Forward snowballing** = papers citing each seed paper.

The script writes CSVs that can be used directly for literature screening, citation graph building, and novelty-gap analysis.

## Important note

The current ChatGPT runtime could not resolve `api.openalex.org` or `api.semanticscholar.org` directly, so this package is designed to be run locally, in Codex, or in any internet-enabled Python environment. It uses the public APIs and caches all responses for reproducibility.

## Folder structure

```text
input/
  seed_papers_manifest.csv          # cleaned seed list with DOI/arXiv/PMID/PMCID where available
  seed_papers_original.csv          # original paper citation CSV
  paper_download_links_curated.csv  # previous legal download-link list
scripts/
  collect_openalex_semantic_scholar_snowball.py
outputs/
  # generated after running
requirements.txt
run_snowball.sh
run_snowball.ps1
CODEX_PROMPT.md
```

## Quick run on Windows PowerShell

```powershell
cd agri_cv_snowball_package
$env:OPENALEX_MAILTO = "your.email@example.com"  # recommended for OpenAlex polite pool
$env:S2_API_KEY = "your_semantic_scholar_api_key" # optional but recommended
.\run_snowball.ps1
```

## Quick run on Linux/macOS/Git Bash

```bash
cd agri_cv_snowball_package
export OPENALEX_MAILTO="your.email@example.com"   # recommended
export S2_API_KEY="your_semantic_scholar_api_key" # optional but recommended
./run_snowball.sh
```

## Manual run

```bash
python scripts/collect_openalex_semantic_scholar_snowball.py \
  --input input/seed_papers_manifest.csv \
  --out outputs \
  --mailto "$OPENALEX_MAILTO" \
  --s2-api-key "$S2_API_KEY" \
  --providers both
```

## Output files

| File | Meaning |
|---|---|
| `seed_papers_provider_metadata.csv` | One row per seed-provider match. Contains OpenAlex and Semantic Scholar metadata separately. |
| `seed_papers_merged_metadata.csv` | One merged row per seed paper, useful as the main seed bibliography table. |
| `backward_references.csv` | All references used by each seed paper, provider-separated. |
| `forward_citations.csv` | All citing papers for each seed paper, provider-separated. |
| `snowball_edges.csv` | Combined citation edge table. For backward references: seed -> reference. For forward citations: citing paper -> seed. |
| `snowball_nodes.csv` | Deduplicated paper/node table for seeds, references, and citing papers. |
| `run_summary.csv` | Counts per seed/provider: reported references/citations and downloaded rows. |
| `unresolved_seeds.csv` | Any failed or low-confidence provider matches. |
| `run_manifest.json` | Run settings and output counts. |
| `cache/` | Cached API JSON responses for reproducibility and restartability. |
| `raw_seed_records/` | Raw OpenAlex/Semantic Scholar seed records. |

## Useful options

```bash
# OpenAlex only
python scripts/collect_openalex_semantic_scholar_snowball.py --providers openalex

# Semantic Scholar only
python scripts/collect_openalex_semantic_scholar_snowball.py --providers semantic_scholar

# Limit forward citations during a smoke test
python scripts/collect_openalex_semantic_scholar_snowball.py --max-forward-citations 10 --max-backward-references 10

# Reuse cached results by default; force fresh API calls
python scripts/collect_openalex_semantic_scholar_snowball.py --refresh-cache
```

## Seed caveats

- `P004 MFO` and `P010 WeedsGalore` may resolve by title because the original rows did not include DOI values.
- `P013 TomatoPGT ecosystem` was already marked as uncertain in the curated CSV. Verify its bibliographic title/authors manually before using it in a manuscript bibliography.
- Provider citation counts can differ between OpenAlex and Semantic Scholar because they index and deduplicate literature differently.

## Recommended next analysis after collection

1. Sort `forward_citations.csv` by year descending and citation count descending to identify recent follow-up work.
2. Filter `backward_references.csv` for recurring references across seeds to identify methodological baselines.
3. Use `snowball_nodes.csv` to rank papers by overlap with multiple seeds.
4. Screen papers with titles containing: segmentation, multispectral, hyperspectral, UAV, phenotyping, fruit detection, weed, disease, 3D, point cloud, foundation model, SAM, transformer, domain adaptation, self-supervised, semi-supervised.
5. Build a PRISMA-style screening table from `snowball_nodes.csv`.
