#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT="${1:-outputs/snowball_manual_$(date -u +%Y-%m-%d_%H%M)}"
SEED_IDS="${2:-}"
cd "$REPO_ROOT"
ARGS=(
  tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py
  --input tools/agri_cv_snowball_package/input/seed_papers_manifest.csv
  --out "$OUT"
  --providers both
)
if [[ -n "$SEED_IDS" ]]; then ARGS+=(--seed-ids "$SEED_IDS"); fi
uv run python "${ARGS[@]}"
