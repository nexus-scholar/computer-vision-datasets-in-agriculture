from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

decisions_path = REPO / "data/curated/screening/full_text_decisions.csv"
ranking_path = REPO / "outputs/fulltext_ranking/runs/RANK_20260722T210245Z/recommended_fulltext_queue.csv"
screening_path = REPO / "data/curated/screening/title_abstract_decisions.csv"

_, decision_rows = read_csv(decisions_path)
_, ranking_rows = read_csv(ranking_path)
_, screening_rows = read_csv(screening_path)

decided_ids = {}
for row in decision_rows:
    cid = (row.get("paper_id") or row.get("candidate_id") or "").strip()
    if cid:
        decided_ids[cid] = row

active_ids = set()
for row in screening_rows:
    if (row.get("decision") or "").strip().lower() in ("include", "unclear"):
        cid = (row.get("candidate_id") or "").strip()
        if cid:
            active_ids.add(cid)

ranked_ids = [r.get("candidate_id", "").strip() for r in ranking_rows]
ranked_set = set(ranked_ids)

pending = [r for r in ranking_rows if r.get("candidate_id", "").strip() not in decided_ids]
pending_ids = [r.get("candidate_id", "").strip() for r in pending]

print(f"decisions rows: {len(decision_rows)}  unique ids: {len(decided_ids)}")
print(f"ranking rows: {len(ranking_rows)}  unique ids: {len(ranked_set)}")
print(f"active (TA include/unclear) ids: {len(active_ids)}")
print(f"pending (ranking, not decided): {len(pending)}")
print(f"pending unique: {len(set(pending_ids))}")

missing_from_active = [i for i in pending_ids if i not in active_ids]
print(f"pending not in TA-active: {len(missing_from_active)}")
for i in missing_from_active[:10]:
    print(f"  {i}")

not_in_ranking = active_ids - decided_ids.keys() - ranked_set
print(f"TA-active undecided but NOT in ranking file: {len(not_in_ranking)}")
for i in sorted(not_in_ranking)[:10]:
    print(f"  {i}")
