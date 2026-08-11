from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

corpora = [
    REPO / "outputs/screening_queue_2026-07-22/screening_queue.csv",
    REPO / "data/curated/screening/title_abstract_decisions_enriched.csv",
    REPO / "data/curated/screening/full_text_decisions.csv",
    REPO / "outputs/fulltext_ranking/runs/RANK_20260722T210245Z/recommended_fulltext_queue.csv",
]

def norm_doi(v: str) -> str:
    return (v or "").strip().lower().replace("https://doi.org/", "").replace("http://dx.doi.org/", "").replace("doi:", "")

def norm_title(v: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", " ", (v or "").lower()).strip()

lookups = {
    "cicba2017a": {"keys": ["fruit recognition and classification"], "want_doi": "", "want_arxiv": ""},
    "Estimating_the_LAI_IROS2017": {"keys": ["estimating the lai", "leaf area index"], "want_doi": "", "want_arxiv": ""},
    "Overview_of_the_radiometric_and_biophysi": {"keys": ["radiometric and biophysical"], "want_doi": "", "want_arxiv": ""},
    "s41597-026-07074-w": {"keys": ["multimodal holistic dataset", "horticultural tomato"], "want_doi": "10.1038/s41597-026-07074-w", "want_arxiv": ""},
    "2310.11516": {"keys": [], "want_doi": "", "want_arxiv": "2310.11516"},
    "chong2023ral": {"keys": [], "want_doi": "", "want_arxiv": ""},
    "marks2022icra": {"keys": [], "want_doi": "", "want_arxiv": ""},
    "ECPA23": {"keys": [], "want_doi": "", "want_arxiv": ""},
    "s41597-026-06926-9": {"keys": [], "want_doi": "10.1038/s41597-026-06926-9", "want_arxiv": ""},
}

seen_ids = set()
rows_all = []
for cp in corpora:
    if not cp.exists():
        continue
    _, rows = read_csv(cp)
    for r in rows:
        pid = r.get("paper_id") or r.get("candidate_id") or ""
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        rows_all.append({**r, "__src": cp.name})

def show_match(label: str, cond) -> None:
    hits = [r for r in rows_all if cond(r)]
    print(f"\n=== {label}: {len(hits)} hit(s)")
    for r in hits[:5]:
        print("  ", r.get("__src"), "|", r.get("candidate_id") or r.get("paper_id"), "| doi:", r.get("doi", ""), "| arxiv:", r.get("arxiv_id", ""), "| title:", (r.get("title") or "")[:80])

for label, spec in lookups.items():
    if spec["want_doi"]:
        show_match(label, lambda r, d=spec["want_doi"]: norm_doi(r.get("doi", "")) == d)
    elif spec["want_arxiv"]:
        show_match(label, lambda r, a=spec["want_arxiv"]: (r.get("arxiv_id") or "").strip().replace("arxiv:", "").startswith(a))
    elif spec["keys"]:
        for key in spec["keys"]:
            show_match(f"{label} [{key}]", lambda r, k=key: norm_title(r.get("title", ""))[:60] == k or k in norm_title(r.get("title", "")))
    else:
        print(f"\n=== {label}: no machine-readable hint; searching titles by author pattern")
        low = label.lower()
        hits = [r for r in rows_all if low.replace("20", "") in norm_title(r.get("title", "")) or label.split("20")[0][:6] in (r.get("title") or "").lower()]
        print(f"  {len(hits)} hit(s)")
        for r in hits[:5]:
            print("  ", r.get("__src"), "|", r.get("candidate_id") or r.get("paper_id"), "| doi:", r.get("doi", ""), "| arxiv:", r.get("arxiv_id", ""), "| title:", (r.get("title") or "")[:80])

print("\n--- candidate_ids containing 'titleyear:' (id-less papers) ---")
for r in rows_all:
    cid = r.get("candidate_id") or r.get("paper_id") or ""
    if "titleyear:" in str(cid) or "no_identifier" in str(cid).lower():
        print("  ", cid[:80], "| title:", (r.get("title") or "")[:70])
