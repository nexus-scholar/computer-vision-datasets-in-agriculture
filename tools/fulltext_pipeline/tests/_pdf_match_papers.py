from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

_, ranking = read_csv(REPO / "outputs/fulltext_ranking/runs/RANK_20260722T210245Z/recommended_fulltext_queue.csv")
_, artifacts = read_csv(REPO / "data/curated/fulltext/artifact_registry.csv")
_, decisions = read_csv(REPO / "data/curated/screening/full_text_decisions.csv")

def norm_doi(v: str) -> str:
    return re.sub(r"^https?://doi\.org/|^doi:", "", (v or "").strip().lower()).strip()

def norm_title(v: str) -> str:
    t = re.sub(r"<[^>]+>", " ", v or "")
    t = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    return t

by_doi: dict[str, dict] = {}
by_arxiv: dict[str, dict] = {}
by_rank: dict[int, dict] = {}
by_title_norm: dict[str, dict] = {}
for r in ranking:
    pid = r.get("candidate_id", "").strip()
    doi = norm_doi(r.get("doi", ""))
    if doi:
        by_doi.setdefault(doi, r)
    arx = (r.get("arxiv_id", "") or "").strip().lower().replace("arxiv:", "")
    if arx:
        by_arxiv.setdefault(arx, r)
    try:
        by_rank[int(r.get("original_screening_rank", "") or 0)] = r
    except ValueError:
        pass
    tn = norm_title(r.get("title", ""))
    if tn:
        by_title_norm.setdefault(tn, r)

paper_ids_with_pdf = {row.get("paper_id", "") for row in artifacts if row.get("status") == "success" and row.get("artifact_type") == "pdf"}
decided = {r.get("paper_id", "").strip() for r in decisions}
fu1 = {r.get("paper_id", "").strip() for r in decisions if (r.get("decision") or "").lower() == "unresolved"}

idents = json.loads((REPO / "outputs/manual_pdf_identities_20260803.json").read_text(encoding="utf-8"))

def fuzzy(title: str) -> list[tuple[dict, float]]:
    tn = norm_title(title)
    cands = []
    for key, row in by_title_norm.items():
        import difflib
        ratio = difflib.SequenceMatcher(None, tn, key).ratio()
        if ratio >= 0.9:
            cands.append((row, ratio))
    cands.sort(key=lambda x: -x[1])
    return cands[:3]

results = []
for rec in idents:
    pid_matched = ""
    match_method = ""
    conf = ""
    note = ""
    row = None
    for d in rec.get("dois_first", []):
        if norm_doi(d) in by_doi:
            row = by_doi[norm_doi(d)]
            pid_matched = row.get("candidate_id", "")
            match_method = f"doi:{d}"
            conf = "high"
            break
    if row is None:
        for a in rec.get("arxiv_first", []):
            key = a.lower()
            if key in by_arxiv:
                row = by_arxiv[key]
                pid_matched = row.get("candidate_id", "")
                match_method = f"arxiv:{a}"
                conf = "high"
                break
    if row is None:
        t = rec.get("meta_title") or (rec.get("first_text") or "").split("\n")[0]
        fuzzy_hits = fuzzy(t)
        if fuzzy_hits:
            row, ratio = fuzzy_hits[0]
            pid_matched = row.get("candidate_id", "")
            match_method = f"title:{t[:70]}"
            conf = "high" if ratio >= 0.98 else ("medium" if ratio >= 0.94 else "low")
            if len(fuzzy_hits) > 1 and abs(fuzzy_hits[0][1] - fuzzy_hits[1][1]) < 0.02:
                conf = "ambiguous"
                note = "close 2nd: " + fuzzy_hits[1][0].get("title", "")[:60]
    results.append({
        "file": rec["file"],
        "sha256": rec.get("sha256", ""),
        "size_bytes": rec.get("size_bytes", 0),
        "pages": rec.get("pages", 0),
        "pdf_doi": ";".join(rec.get("dois_first", [])) or "",
        "pdf_arxiv": ";".join(rec.get("arxiv_first", [])) or "",
        "pdf_meta_title": (rec.get("meta_title") or "")[:120],
        "matched_paper_id": pid_matched,
        "match_method": match_method,
        "confidence": conf,
        "note": note,
        "screening_rank": row.get("original_screening_rank", "") if row else "",
        "title": row.get("title", "") if row else "",
        "undecided": "yes" if (pid_matched and pid_matched not in decided) else "no",
        "fu1": "yes" if pid_matched in fu1 else "no",
        "has_pdf": "yes" if pid_matched in paper_ids_with_pdf else "no",
    })

json_out = REPO / "outputs/manual_pdf_matches_20260803.json"
json_out.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")

print(f"total: {len(results)}")
print("matched:", sum(1 for r in results if r['matched_paper_id']))
print("unmatched:", sum(1 for r in results if not r['matched_paper_id']))
print("confidence:", {k: sum(1 for r in results if r['confidence'] == k) for k in ['high','medium','low','ambiguous']})
print("undecided target:", sum(1 for r in results if r['undecided'] == 'yes'))
print("fu1 target:", sum(1 for r in results if r['fu1'] == 'yes'))
print("already has pdf:", sum(1 for r in results if r['has_pdf'] == 'yes'))
print()
print("UNMATCHED:")
for r in results:
    if not r['matched_paper_id']:
        print(" -", r['file'], "| doi:", r['pdf_doi'], "| arxiv:", r['pdf_arxiv'], "| meta:", r['pdf_meta_title'][:80])
