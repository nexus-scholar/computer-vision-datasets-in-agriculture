$ErrorActionPreference = "Stop"

# Optional but recommended before running:
# $env:OPENALEX_MAILTO = "your.email@example.com"
# $env:S2_API_KEY = "your_semantic_scholar_api_key"

python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/collect_openalex_semantic_scholar_snowball.py `
  --input input/seed_papers_manifest.csv `
  --out outputs `
  --mailto "$env:OPENALEX_MAILTO" `
  --s2-api-key "$env:S2_API_KEY" `
  --providers both
