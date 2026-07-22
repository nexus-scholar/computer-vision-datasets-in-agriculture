# Codex task: run agriculture CV paper snowballing metadata collection

You are in a folder containing a prepared snowballing package for 13 agriculture computer-vision dataset papers.

Goal: use OpenAlex and Semantic Scholar Graph API to collect:

1. full provider metadata for each seed paper,
2. backward snowballing: all references used by each seed paper,
3. forward snowballing: all papers that cite each seed paper,
4. a unified edge list and node table suitable for later screening, ranking, or graph analysis.

Steps:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export OPENALEX_MAILTO="<your email>"   # optional but recommended
export S2_API_KEY="<your S2 API key>"    # optional, recommended for fewer rate-limit errors
python scripts/collect_openalex_semantic_scholar_snowball.py \
  --input input/seed_papers_manifest.csv \
  --out outputs \
  --mailto "$OPENALEX_MAILTO" \
  --s2-api-key "$S2_API_KEY" \
  --providers both
```

Expected outputs in `outputs/`:

- `seed_papers_provider_metadata.csv`
- `seed_papers_merged_metadata.csv`
- `backward_references.csv`
- `forward_citations.csv`
- `snowball_edges.csv`
- `snowball_nodes.csv`
- `run_summary.csv`
- `unresolved_seeds.csv`
- `run_manifest.json`
- `cache/*.json`
- `raw_seed_records/*.json`

After running, inspect `unresolved_seeds.csv`. For unresolved or low-confidence rows, manually check the title in OpenAlex/Semantic Scholar web search, then rerun using the same cache after correcting `input/seed_papers_manifest.csv` with DOI, arXiv ID, PMID, PMCID, or an exact title.

Recommended quality checks:

- Verify that each seed has one OpenAlex and/or Semantic Scholar match.
- Compare title/year between input and provider metadata.
- For `P013 TomatoPGT ecosystem`, verify bibliographic details manually because the original citation was marked as uncertain.
- Deduplicate downstream literature primarily by DOI, then OpenAlex ID, then Semantic Scholar paper ID, then title+year.
- Keep `cache/` for reproducibility.
