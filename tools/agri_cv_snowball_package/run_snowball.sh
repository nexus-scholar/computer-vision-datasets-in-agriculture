#!/usr/bin/env bash
set -euo pipefail

# Optional but recommended:
# export OPENALEX_MAILTO="your.email@example.com"
# export S2_API_KEY="your_semantic_scholar_api_key"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/collect_openalex_semantic_scholar_snowball.py \
  --input input/seed_papers_manifest.csv \
  --out outputs \
  --mailto "${OPENALEX_MAILTO:-}" \
  --s2-api-key "${S2_API_KEY:-}" \
  --providers both
