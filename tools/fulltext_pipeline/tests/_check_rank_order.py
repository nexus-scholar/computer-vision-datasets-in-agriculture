from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import atomic_write_csv, read_csv

out_dir = REPO / "outputs/fulltext_ranking"
ranking_path = REPO / "outputs/fulltext_ranking/runs/RANK_20260722T210245Z/recommended_fulltext_queue.csv"

_, ranking_rows = read_csv(ranking_path)
_, decision_rows = read_csv(REPO / "data/curated/screening/full_text_decisions.csv")

decided_ids = set()
for row in decision_rows:
    cid = (row.get("paper_id") or row.get("candidate_id") or "").strip()
    if cid:
        decided_ids.add(cid)

pending = [r for r in ranking_rows if r.get("candidate_id", "").strip() not in decided_ids]
assert len(pending) == 146, f"expected 146 pending, got {len(pending)}"

rank_vals = [r.get("recommended_fulltext_rank") or "" for r in pending]
num = [int(v) for v in rank_vals if v.strip().isdigit()]
print(f"pending rows with numeric recommended_fulltext_rank: {len(num)}/{len(pending)}")
print(f"first 10 recommended_fulltext_rank values: {num[:10]}")
print(f"monotonic increasing: {all(a < b for a, b in zip(num, num[1:]))}")

included_order = [r.get("included_order") or "" for r in pending]
print(f"first 10 included_order values: {included_order[:10]}")

fields = [h for h in (ranking_rows[0].keys() if ranking_rows else [])]
pending_rank_file = out_dir / "pending_146_fulltext.csv"
atomic_write_csv(pending_rank_file, list(fields), pending)
print(f"wrote {pending_rank_file.name}: {len(pending)} rows")

chunk_size = 50
for i in range(0, len(pending), chunk_size):
    chunk = pending[i : i + chunk_size]
    idx = i // chunk_size + 1
    path = out_dir / f"pending_acq_{idx}_of_3.csv"
    atomic_write_csv(path, list(fields), chunk)
    print(f"wrote {path.name}: {len(chunk)} rows")
