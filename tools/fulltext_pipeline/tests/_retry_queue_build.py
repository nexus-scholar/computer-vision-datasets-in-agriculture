from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import atomic_write_csv, read_csv

out_dir = REPO / "outputs/fulltext_ranking"
_, pending = read_csv(out_dir / "pending_146_fulltext.csv")
_, artifacts = read_csv(REPO / "data/curated/fulltext/artifact_registry.csv")

covered = {row.get("paper_id", "") for row in artifacts if row.get("status") == "success"}
retry = [r for r in pending if r.get("candidate_id", "").strip() not in covered]
print(f"pending: {len(pending)}  covered: {len(covered & {r.get('candidate_id','').strip() for r in pending})}  retry: {len(retry)}")

fields = list(pending[0].keys()) if pending else []
for i in range(0, len(retry), 50):
    chunk = retry[i : i + 50]
    idx = i // 50 + 1
    path = out_dir / f"pending_retry_{idx}_of_{len([x for x in range(0, len(retry), 50)])}.csv"
    atomic_write_csv(path, fields, chunk)
    print(f"wrote {path.name}: {len(chunk)} rows")
