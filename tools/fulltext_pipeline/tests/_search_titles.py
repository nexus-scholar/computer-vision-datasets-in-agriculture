from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

corpora = [
    (REPO / "outputs/screening_queue_2026-07-22/screening_queue.csv", "queue"),
    (REPO / "data/curated/screening/title_abstract_decisions_enriched.csv", "ta_decisions"),
    (REPO / "data/curated/screening/full_text_decisions.csv", "ft_decisions"),
]

def norm_title(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (v or "").lower()).strip()

keys = [
    "unsupervised generation of labeled training images for crop weed",
    "precise 3d reconstruction of plants from uav imagery",
    "automatic estimation of trunk cross sectional area using deep learning",
    "field robot for high throughput and high resolution 3d plant phenotyping",
    "tomato multi angle multi pose dataset",
    "a three year multimodal holistic dataset for horticultural tomato",
    "shape based fruit recognition and classification",
    "estimating the leaf area index of crops through the evaluation of 3d models",
    "overview of the radiometric and biophysical performance of the modis vegetation indices",
]

seen = set()
rows_all = []
for cp, src in corpora:
    _, rows = read_csv(cp)
    for r in rows:
        pid = r.get("paper_id") or r.get("candidate_id") or ""
        if pid in seen:
            continue
        seen.add(pid)
        rows_all.append({**r, "__src": src})

for key in keys:
    hits = [r for r in rows_all if norm_title(r.get("title", "")).startswith(key[:40]) or key in norm_title(r.get("title", ""))]
    print(f"\n=== [{key}] {len(hits)} hit(s)")
    for r in hits:
        print("   src:", r["__src"],
              "| id:", r.get("candidate_id") or r.get("paper_id"),
              "| doi:", r.get("doi", ""),
              "| arxiv:", r.get("arxiv_id", ""),
              "| decision:", r.get("decision", ""),
              "| rank:", r.get("rank", ""),
              "| title:", (r.get("title") or "")[:75])
