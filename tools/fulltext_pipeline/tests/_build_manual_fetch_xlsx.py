from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

ACQ_ROOT = REPO / "outputs/fulltext/acquisition"
B8_RUNS = ["FTA_20260803T124948Z", "FTA_20260803T130215Z", "FTA_20260803T131505Z",
           "FTA_20260803T154719Z", "FTA_20260803T155333Z", "FTA_20260803T160244Z"]
B7_RUN = "FTA_20260803T005806Z"
SOURCE_PREF = ["direct", "pmc_id_converter", "pmc_oai", "europe_pmc", "arxiv", "unpaywall", "crossref", "openalex", "semantic_scholar"]

_, pending = read_csv(REPO / "outputs/fulltext_ranking/pending_146_fulltext.csv")
_, artifacts = read_csv(REPO / "data/curated/fulltext/artifact_registry.csv")

art_types: dict[str, set[str]] = {}
for row in artifacts:
    if row.get("status") == "success":
        art_types.setdefault(row.get("paper_id", ""), set()).add(row.get("artifact_type", ""))

_, decisions = read_csv(REPO / "data/curated/screening/full_text_decisions.csv")
fu1 = [r for r in decisions if (r.get("decision") or "").lower() == "unresolved"]
fu1_ids = {r.get("paper_id", "") for r in fu1}

def load_summaries(runs: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for rid in runs:
        path = ACQ_ROOT / rid / "summary.csv"
        if not path.exists():
            continue
        _, rows = read_csv(path)
        for r in rows:
            out[r.get("paper_id", "")] = r
    return out

def load_best_candidates(runs: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for rid in runs:
        path = ACQ_ROOT / rid / "candidates.csv"
        if not path.exists():
            continue
        _, rows = read_csv(path)
        for r in rows:
            pid = r.get("paper_id", "")
            atype = r.get("artifact_type", "")
            try:
                score = float(r.get("score") or 0)
            except ValueError:
                score = 0
            source = r.get("source", "")
            cur = out.get(pid, {})
            key = f"{atype}_url"
            if key not in cur:
                cur[key] = r.get("url", "")
                cur[f"{atype}_source"] = source
                cur[f"{atype}_rights"] = r.get("rights_status", "")
            else:
                cur_score = float(cur.get(f"{atype}_score", -1))
                if score > cur_score or (score == cur_score and SOURCE_PREF.index(source) < SOURCE_PREF.index(cur.get(f"{atype}_source", "zzz"))):
                    cur[key] = r.get("url", "")
                    cur[f"{atype}_source"] = source
                    cur[f"{atype}_rights"] = r.get("rights_status", "")
            cur[f"{atype}_score"] = str(max(float(cur.get(f"{atype}_score", -1)), score))
            out[pid] = cur
    return out

b8_summary = load_summaries(B8_RUNS)
b7_summary = load_summaries([B7_RUN])
b8_cands = load_best_candidates(B8_RUNS)
b7_cands = load_best_candidates([B7_RUN])

def status_text(pid: str) -> str:
    types = art_types.get(pid, set())
    has_pdf = "pdf" in types
    has_xml = bool(types & {"jats_xml", "tei_xml", "xml"})
    return has_pdf, has_xml

rows = []
for r in pending:
    pid = r.get("candidate_id", "").strip()
    has_pdf, has_xml = status_text(pid)
    if has_pdf:
        continue
    s = b8_summary.get(pid, {})
    c = b8_cands.get(pid, {})
    rows.append({
        "recommended_fulltext_rank": r.get("recommended_fulltext_rank", ""),
        "screening_rank": r.get("original_screening_rank", ""),
        "paper_id": pid,
        "title": r.get("title", ""),
        "year": r.get("year", ""),
        "venue": r.get("venue", "") or r.get("journal", ""),
        "authors": r.get("authors", ""),
        "doi": r.get("doi", ""),
        "arxiv_id": r.get("arxiv_id", ""),
        "is_open_access": r.get("is_open_access", ""),
        "landing_url": r.get("landing_url", ""),
        "best_pdf_url": c.get("pdf_url", ""),
        "pdf_url_source": c.get("pdf_source", ""),
        "pdf_url_rights": c.get("pdf_rights", ""),
        "any_candidate_url": c.get("pdf_url", "") or c.get("structured_url", "") or r.get("landing_url", ""),
        "has_xml": "yes" if has_xml else "no",
        "artifact_status": "xml_only" if has_xml else "none",
        "last_pdf_result": s.get("pdf_result", ""),
        "last_xml_result": s.get("structured_result", ""),
        "candidate_count": s.get("candidate_count", ""),
        "resolver_error_count": s.get("resolver_error_count", ""),
    })

df_undecided = pd.DataFrame(rows)
if not df_undecided.empty:
    df_undecided = df_undecided.sort_values("recommended_fulltext_rank", key=lambda x: pd.to_numeric(x, errors="coerce"))

fu_rows = []
for d in fu1:
    pid = d.get("paper_id", "").strip()
    has_pdf, has_xml = status_text(pid)
    s = b7_summary.get(pid, {})
    c = b7_cands.get(pid, {})
    fu_rows.append({
        "screening_rank": d.get("rank", ""),
        "paper_id": pid,
        "title": d.get("title", ""),
        "decision": d.get("decision", ""),
        "reason_code": d.get("reason_code", ""),
        "reviewed_at": d.get("reviewed_at", ""),
        "best_pdf_url": c.get("pdf_url", ""),
        "pdf_url_source": c.get("pdf_source", ""),
        "any_candidate_url": c.get("pdf_url", "") or c.get("structured_url", ""),
        "has_pdf": "yes" if has_pdf else "no",
        "has_xml": "yes" if has_xml else "no",
        "last_pdf_result": s.get("pdf_result", ""),
        "last_xml_result": s.get("structured_result", ""),
    })

df_fu = pd.DataFrame(fu_rows)

out_path = REPO / "outputs/manual_pdf_fetch_worklist_20260803.xlsx"
with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
    df_undecided.to_excel(writer, sheet_name="Undecided_Need_PDF", index=False)
    df_fu.to_excel(writer, sheet_name="Unresolved_FU1_Need_PDF", index=False)
    wb = writer.book
    for ws in wb.worksheets:
        for col in ws.columns:
            width = max((len(str(cell.value)) for cell in col if cell.value is not None), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 80)

print(f"wrote {out_path}")
print(f"undecided rows needing PDF: {len(df_undecided)}")
print(f"batch-7 FU1 rows: {len(df_fu)}")
if not df_undecided.empty:
    print("artifact_status counts:", df_undecided["artifact_status"].value_counts().to_dict())
    print("no candidate url rows:", (df_undecided["any_candidate_url"] == "").sum())
