from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

FILES = [r["path"] for r in json.loads((REPO / "outputs/manual_pdf_identities_20260803.json").read_text(encoding="utf-8"))]
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"',;\)\]\\]+")
ARX_RE = re.compile(r"arXiv:?\s*(\d{4}\.\d{4,5})", re.IGNORECASE)

def norm_doi(v: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/|^doi:", "", (v or "").strip().lower()).strip()

def norm_title(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"<[^>]+>", " ", (v or "").lower())).strip()

_, ta = read_csv(REPO / "data/curated/screening/title_abstract_decisions_enriched.csv")
_, ft = read_csv(REPO / "data/curated/screening/full_text_decisions.csv")
_, arts = read_csv(REPO / "data/curated/fulltext/artifact_registry.csv")

eligible = [r for r in ta if (r.get("decision") or "").strip().lower() in ("include", "unclear")]
by_doi: dict[str, dict] = {}
by_arxiv: dict[str, dict] = {}
by_title: dict[str, list] = {}
for r in eligible:
    pid = (r.get("candidate_id") or r.get("paper_id") or "").strip()
    doi = norm_doi(r.get("doi", ""))
    if doi:
        by_doi.setdefault(doi, r)
    arx = (r.get("arxiv_id") or "").strip().lower().replace("arxiv:", "")
    if arx:
        by_arxiv.setdefault(arx, r)
    key = norm_title(r.get("title", ""))
    if key:
        by_title.setdefault(key, []).append(r)

decided_ft = {r.get("paper_id", "").strip() for r in ft}
fu1 = {r.get("paper_id", "").strip() for r in ft if (r.get("decision") or "").lower() == "unresolved"}
pdf_papers = {r.get("paper_id", "") for r in arts if r.get("status") == "success" and r.get("artifact_type") == "pdf"}

def match_title(title: str):
    key = norm_title(title)
    if key in by_title:
        return by_title[key][0], 1.0
    if not key:
        return None, 0.0
    best = None
    best_ratio = 0.0
    for k, rows in by_title.items():
        if not k:
            continue
        ratio = difflib.SequenceMatcher(None, key, k).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = rows[0]
    return best, best_ratio

out = []
for path_str in FILES:
    rec = {"file": Path(path_str).name, "path": path_str}
    try:
        doc = fitz.open(path_str)
        text = " ".join(doc[i].get_text() for i in range(min(doc.page_count, 3)))
        doc.close()
        text = re.sub(r"\s+", " ", text)
        dois = [norm_doi(d) for d in DOI_RE.findall(text)]
        arx = [a.lower() for a in ARX_RE.findall(text)]
        row = None
        method = ""
        for d in dois:
            if d in by_doi:
                row = by_doi[d]
                method = "doi:" + d
                break
        if row is None:
            for a in arx:
                if a in by_arxiv:
                    row = by_arxiv[a]
                    method = "arxiv:" + a
                    break
        conf = "high" if row else ""
        if row is None:
            # title from first lines
            doc = fitz.open(path_str)
            first_lines = [l.strip() for l in doc[0].get_text().split("\n") if l.strip()][:4]
            doc.close()
            candidate_title = " ".join(first_lines[:2])
            row, ratio = match_title(candidate_title)
            method = f"title:{candidate_title[:60]}"
            conf = "high" if ratio >= 0.98 else ("medium" if ratio >= 0.92 else "low")
        pid = (row.get("candidate_id") or row.get("paper_id") or "").strip() if row else ""
        rec.update({
            "pdf_dois": ";".join(d for d in dois[:3]) if dois else "",
            "pdf_arxiv": ";".join(arx[:2]) if arx else "",
            "matched_paper_id": pid,
            "match_method": method,
            "confidence": conf,
            "screening_rank": row.get("rank", "") if row else "",
            "paper_title": (row.get("title") or "") if row else "",
            "in_eligible": "yes" if row else "no",
            "undecided_ft": "yes" if (pid and pid not in decided_ft) else "no",
            "fu1": "yes" if pid in fu1 else "no",
            "already_has_pdf": "yes" if pid in pdf_papers else "no",
        })
    except Exception as exc:
        rec["error"] = str(exc)
    out.append(rec)

json_out = REPO / "outputs/manual_pdf_matches_v2_20260803.json"
json_out.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

print(f"total: {len(out)}")
print("matched:", sum(1 for r in out if r.get("matched_paper_id")))
print("unmatched:", sum(1 for r in out if not r.get("matched_paper_id")))
print("conf:", {k: sum(1 for r in out if r.get('confidence') == k) for k in ('high','medium','low')})
print("undecided targets:", sum(1 for r in out if r.get("undecided_ft") == "yes"))
print("FU1 targets:", sum(1 for r in out if r.get("fu1") == "yes"))
print("already decided(incl core/support):", sum(1 for r in out if r.get("matched_paper_id") and r.get("undecided_ft") == "no" and r.get("fu1") == "no"))
print("already has pdf:", sum(1 for r in out if r.get("already_has_pdf") == "yes"))
print()
for r in out:
    if not r.get("matched_paper_id"):
        print("NO MATCH:", r["file"], "| doi:", r.get("pdf_dois"), "| arxiv:", r.get("pdf_arxiv"))
