from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from . import database
import pandas as pd

router = APIRouter()

import math

COLORS = {
    "include": "bg-green-100 text-green-800",
    "exclude": "bg-red-100 text-red-800",
    "unclear": "bg-yellow-100 text-yellow-800",
    "high": "bg-blue-100 text-blue-800",
    "medium": "bg-indigo-100 text-indigo-800",
    "low": "bg-gray-100 text-gray-600",
}


def _val(v, default=""):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return str(v)


def _tag(text, cls):
    return f'<span class="inline-block px-2 py-0.5 rounded text-xs font-medium {cls}">{text}</span>'


def _link(rank, title, maxlen=75):
    tr = title[:maxlen] + ("..." if len(title) > maxlen - 1 else "")
    esc_title = title.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return f'<a href="#" class="paper-link text-brand-700 hover:underline font-medium" data-rank="{rank}" title="{esc_title}">{tr}</a>'


def _unique_from_col(df, col):
    vals = set()
    for v in df[col].dropna():
        for part in str(v).split(";"):
            vals.add(part.strip())
    return sorted(vals)


def _filt(endpoint, target, name, placeholder, value):
    val = f' value="{value}"' if value else ""
    return (f'<input type="text" name="{name}" placeholder="{placeholder}"{val}'
            f' class="w-56 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-300"'
            f' hx-get="{endpoint}" hx-target="{target}" hx-trigger="input changed delay:300ms" hx-swap="outerHTML">')


def _filt_sel(endpoint, target, name, options, current):
    opts = "".join(f'<option value="{k}"{" selected" if k == current else ""}>{v}</option>' for k, v in options)
    return (f'<select name="{name}"'
            f' class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-300"'
            f' hx-get="{endpoint}" hx-target="{target}" hx-trigger="change" hx-swap="outerHTML">'
            + opts + '</select>')


@router.get("/api/overview")
def get_overview():
    b = database.batches()
    r = database.ranking()
    s = database.screening()
    t_s = t_i = t_e = t_u = n_b = 0
    if b is not None and not b.empty:
        t_s = int(b["decision_count"].sum()) if "decision_count" in b else 0
        t_i = int(b["included"].sum()) if "included" in b else 0
        t_e = int(b["excluded"].sum()) if "excluded" in b else 0
        t_u = int(b["unclear"].sum()) if "unclear" in b else 0
        n_b = len(b)
    n_fp = n_fs = 0
    if database._extractions is not None and not database._extractions.empty:
        n_fp = len(database._extractions)
        for col in ("docling_status", "grobid_status", "publisher_xml_status"):
            if col in database._extractions.columns:
                n_fs += int(database._extractions[col].eq("success").sum())
    r_t = len(r) if r is not None else 0
    tasks, mods, doms = set(), set(), set()
    if s is not None and not s.empty:
        for row in s["vision_task"].dropna():
            for t in str(row).split(";"):
                tasks.add(t.strip())
        for row in s["modalities"].dropna():
            for m in str(row).split(";"):
                mods.add(m.strip())
        for row in s["agricultural_domain"].dropna():
            for d in str(row).split(";"):
                doms.add(d.strip())

    def tlist(xs):
        return ''.join(f'<span class="bg-gray-100 px-2 py-0.5 rounded text-xs">{x}</span>' for x in sorted(xs)[:12])

    h = ('<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">'
        + '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4"><p class="text-xs text-gray-500 uppercase tracking-wide">Screened</p><p class="text-3xl font-bold text-gray-800">' + str(t_s) + '</p><p class="text-xs text-gray-400">papers</p></div>'
        + '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4"><p class="text-xs text-gray-500 uppercase tracking-wide">Included</p><p class="text-3xl font-bold text-green-600">' + str(t_i) + '</p><p class="text-xs text-gray-400">' + str(t_u) + ' unclear</p></div>'
        + '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4"><p class="text-xs text-gray-500 uppercase tracking-wide">Excluded</p><p class="text-3xl font-bold text-red-600">' + str(t_e) + '</p><p class="text-xs text-gray-400">papers</p></div>'
        + '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4"><p class="text-xs text-gray-500 uppercase tracking-wide">Batches</p><p class="text-3xl font-bold text-gray-800">' + str(n_b) + '</p><p class="text-xs text-gray-400">batches</p></div>'
        + '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4"><p class="text-xs text-gray-500 uppercase tracking-wide">Ranked</p><p class="text-3xl font-bold text-indigo-600">' + str(r_t) + '</p><p class="text-xs text-gray-400">priority scores</p></div>'
        + '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4"><p class="text-xs text-gray-500 uppercase tracking-wide">Full-Text</p><p class="text-3xl font-bold text-purple-600">' + str(n_fp) + '</p><p class="text-xs text-gray-400">' + str(n_fs) + ' processed</p></div>'
        + '</div>'
        + '<div class="flex flex-wrap gap-2 mt-3 text-xs text-gray-500"><span class="font-medium">Tasks:</span>' + tlist(tasks) + '<span class="font-medium ml-2">Modalities:</span>' + tlist(mods) + '<span class="font-medium ml-2">Domains:</span>' + tlist(doms) + '</div>')
    return HTMLResponse(h)


def _render_screening_row(p):
    dec = (p.get("decision") or "").lower()
    conf = (p.get("decision_confidence") or "").lower()
    rank = p.get("rank", "")
    title = p.get("title") or ""
    return ('<tr class="hover:bg-gray-50 border-b border-gray-100">'
        + '<td class="px-3 py-2 text-xs text-gray-400">' + str(rank) + '</td>'
        + '<td class="px-3 py-2 text-sm max-w-md truncate">' + _link(rank, title) + '</td>'
        + '<td class="px-3 py-2">' + _tag(dec, COLORS.get(dec, "bg-gray-100 text-gray-600")) + '</td>'
        + '<td class="px-3 py-2">' + _tag(conf, COLORS.get(conf, "bg-gray-100 text-gray-600")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500 max-w-xs truncate">' + str(p.get("reason_code", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("vision_task", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("modalities", "")) + '</td>'
        + '</tr>')


@router.get("/api/screening")
def get_screening(search: str = "", decision: str = "", task: str = ""):
    df = database.screening()
    if df is None or df.empty:
        return HTMLResponse('<p class="text-gray-400 text-center py-8">No screening data.</p>')

    mask = pd.Series(True, index=df.index)
    if search:
        mask &= df["title"].fillna("").str.lower().str.contains(search.lower(), na=False)
    if decision:
        mask &= df["decision"].fillna("").str.lower() == decision.lower()
    if task:
        mask &= df["vision_task"].fillna("").str.contains(task, na=False)

    filtered = df[mask]
    papers = filtered.to_dict(orient="records")
    inc = int((filtered["decision"] == "include").sum())
    exc = int((filtered["decision"] == "exclude").sum())
    unc = int((filtered["decision"] == "unclear").sum())

    all_tasks = _unique_from_col(df, "vision_task")
    task_opts = [("", "All tasks")] + [(t, t) for t in all_tasks]

    filter_bar = (
        '<div class="flex flex-wrap gap-3 mb-4 items-center">'
        + _filt("/api/screening", "#screening-container", "search", "Search titles...", search)
        + _filt_sel("/api/screening", "#screening-container", "decision",
                     [("", "All decisions"), ("include", "Include"), ("exclude", "Exclude"), ("unclear", "Unclear")], decision)
        + _filt_sel("/api/screening", "#screening-container", "task", task_opts, task)
        + f'<span class="text-xs text-gray-400 ml-auto">{len(papers)} results</span>'
        + '</div>')

    rows = "".join(_render_screening_row(p) for p in papers)
    h = ('<div id="screening-container"><div class="flex items-center justify-between mb-2"><h2 class="text-lg font-bold text-gray-800">Title/Abstract Screening Decisions</h2>'
        + '<div class="flex gap-2 text-sm"><span class="px-2 py-1 bg-green-50 text-green-700 rounded text-xs font-medium">' + str(inc) + ' included</span>'
        + '<span class="px-2 py-1 bg-yellow-50 text-yellow-800 rounded text-xs font-medium">' + str(unc) + ' unclear</span>'
        + '<span class="px-2 py-1 bg-red-50 text-red-700 rounded text-xs font-medium">' + str(exc) + ' excluded</span>'
        + '<span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs font-medium">' + str(len(papers)) + ' total</span></div></div>'
        + filter_bar
        + '<div class="overflow-x-auto"><table class="w-full text-left"><thead><tr class="border-b border-gray-200 text-xs text-gray-500 uppercase">'
        + '<th class="px-3 py-2 font-medium">Rank</th><th class="px-3 py-2 font-medium">Title</th><th class="px-3 py-2 font-medium">Decision</th>'
        + '<th class="px-3 py-2 font-medium">Confidence</th><th class="px-3 py-2 font-medium">Reason</th><th class="px-3 py-2 font-medium">Task</th>'
        + '<th class="px-3 py-2 font-medium">Modalities</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>')
    return HTMLResponse(h)


def _render_ranking_row(p):
    title = p.get("title") or ""
    order = p.get("included_order", "")
    scre_rank = p.get("original_screening_rank") or p.get("included_order", "")
    return ('<tr class="hover:bg-gray-50 border-b border-gray-100">'
        + '<td class="px-3 py-2 text-xs text-gray-400">' + str(order) + '</td>'
        + '<td class="px-3 py-2 text-sm max-w-md truncate">' + _link(scre_rank, title) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("primary_role", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("primary_theme", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("project_fit", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("dataset_evidence_value", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("method_gap_value", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(p.get("score_confidence", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500 max-w-xs truncate">' + str(p.get("dataset_cluster", "")) + '</td>'
        + '</tr>')


@router.get("/api/ranking")
def get_ranking(search: str = "", role: str = "", confidence: str = ""):
    df = database.ranking()
    if df is None or df.empty:
        return HTMLResponse('<p class="text-gray-400 text-center py-8">No priority scores.</p>')

    mask = pd.Series(True, index=df.index)
    if search:
        mask &= df["title"].fillna("").str.lower().str.contains(search.lower(), na=False)
    if role:
        mask &= df["primary_role"].fillna("").str.lower() == role.lower()
    if confidence:
        mask &= df["score_confidence"].fillna("").str.lower() == confidence.lower()

    filtered = df[mask]
    papers = filtered.to_dict(orient="records")

    all_roles = sorted(df["primary_role"].dropna().unique())
    role_opts = [("", "All roles")] + [(r, r) for r in all_roles]

    filter_bar = (
        '<div class="flex flex-wrap gap-3 mb-4 items-center">'
        + _filt("/api/ranking", "#ranking-container", "search", "Search titles...", search)
        + _filt_sel("/api/ranking", "#ranking-container", "role", role_opts, role)
        + _filt_sel("/api/ranking", "#ranking-container", "confidence",
                     [("", "All confidences"), ("high", "High"), ("medium", "Medium"), ("low", "Low")], confidence)
        + f'<span class="text-xs text-gray-400 ml-auto">{len(papers)} results</span>'
        + '</div>')

    rows = "".join(_render_ranking_row(p) for p in papers)
    h = ('<div id="ranking-container"><div class="flex items-center justify-between mb-2"><h2 class="text-lg font-bold text-gray-800">Paper Priority Scores</h2>'
        + '<span class="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">' + str(len(papers)) + ' papers</span></div>'
        + filter_bar
        + '<div class="overflow-x-auto"><table class="w-full text-left"><thead><tr class="border-b border-gray-200 text-xs text-gray-500 uppercase">'
        + '<th class="px-3 py-2 font-medium">Order</th><th class="px-3 py-2 font-medium">Title</th><th class="px-3 py-2 font-medium">Role</th>'
        + '<th class="px-3 py-2 font-medium">Theme</th><th class="px-3 py-2 font-medium">Fit</th><th class="px-3 py-2 font-medium">Evidence</th>'
        + '<th class="px-3 py-2 font-medium">Gap</th><th class="px-3 py-2 font-medium">Conf</th><th class="px-3 py-2 font-medium">Cluster</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>')
    return HTMLResponse(h)


def _render_batch_row(b):
    return ('<tr class="hover:bg-gray-50 border-b border-gray-100">'
        + '<td class="px-3 py-2 text-xs font-mono text-gray-400">' + str(b.get("batch_id", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-800">' + str(b.get("batch_type", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-600">' + str(b.get("ranks", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-600">' + str(b.get("decision_count", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-green-600 font-medium">' + str(b.get("included", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-red-600 font-medium">' + str(b.get("excluded", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-yellow-600 font-medium">' + str(b.get("unclear", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500">' + str(b.get("quality_gates_passed", "")) + '</td>'
        + '<td class="px-3 py-2 text-xs text-gray-500 max-w-xs truncate">' + str((b.get("notes") or "")[:60]) + '</td>'
        + '</tr>')


@router.get("/api/batches")
def get_batches():
    df = database.batches()
    if df is None or df.empty:
        return HTMLResponse('<p class="text-gray-400 text-center py-8">No batch data.</p>')
    batches = df.to_dict(orient="records")
    t_dec = sum(b.get("decision_count") or 0 for b in batches)
    t_inc = sum(b.get("included") or 0 for b in batches)
    t_exc = sum(b.get("excluded") or 0 for b in batches)
    t_unc = sum(b.get("unclear") or 0 for b in batches)
    rows = "".join(_render_batch_row(b) for b in batches)
    h = ('<div class="flex items-center justify-between mb-4"><h2 class="text-lg font-bold text-gray-800">Screening Batches</h2>'
        + '<div class="flex gap-2 text-sm"><span class="px-2 py-1 bg-green-50 text-green-700 rounded text-xs font-medium">' + str(t_inc) + ' included</span>'
        + '<span class="px-2 py-1 bg-red-50 text-red-700 rounded text-xs font-medium">' + str(t_exc) + ' excluded</span>'
        + '<span class="px-2 py-1 bg-yellow-50 text-yellow-800 rounded text-xs font-medium">' + str(t_unc) + ' unclear</span>'
        + '<span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs font-medium">' + str(t_dec) + ' decisions</span></div></div>'
        + '<div class="overflow-x-auto"><table class="w-full text-left"><thead><tr class="border-b border-gray-200 text-xs text-gray-500 uppercase">'
        + '<th class="px-3 py-2 font-medium">Batch</th><th class="px-3 py-2 font-medium">Type</th><th class="px-3 py-2 font-medium">Ranks</th>'
        + '<th class="px-3 py-2 font-medium">Total</th><th class="px-3 py-2 font-medium">Included</th><th class="px-3 py-2 font-medium">Excluded</th>'
        + '<th class="px-3 py-2 font-medium">Unclear</th><th class="px-3 py-2 font-medium">Quality</th><th class="px-3 py-2 font-medium">Notes</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
    return HTMLResponse(h)


def _status_tag(status):
    cls_map = {
        "success": "bg-green-100 text-green-700",
        "failure": "bg-red-100 text-red-700",
        "pending": "bg-yellow-100 text-yellow-800",
        "skipped": "bg-gray-100 text-gray-500",
    }
    s = (status or "").lower()
    return _tag(s if s else "—", cls_map.get(s, "bg-gray-100 text-gray-500"))


@router.get("/api/extractions")
def get_extractions():
    df = database.extractions()
    qa = database.quality_reviews()
    if df is None or df.empty:
        return HTMLResponse('<p class="text-gray-400 text-center py-8">No full-text extraction data.</p>')
    extractions = df.to_dict(orient="records")
    rows = ""
    for e in extractions:
        rank = e.get("rank", "")
        title = e.get("title") or ""
        paper_id = e.get("candidate_id") or e.get("paper_id", "")
        has_qa = ""
        if qa is not None and not qa.empty:
            qa_match = qa[(qa["paper_id"] == paper_id) | (qa.get("candidate_id", "") == paper_id)]
            if not qa_match.empty:
                q = qa_match.iloc[0]
                qa_score = _val(q.get("text_quality", ""))
                has_qa = _tag(qa_score, "bg-blue-100 text-blue-700") if qa_score else ""
        rows += ('<tr class="hover:bg-gray-50 border-b border-gray-100">'
            + '<td class="px-3 py-2 text-xs text-gray-400">' + str(rank) + '</td>'
            + '<td class="px-3 py-2 text-sm max-w-sm truncate">' + _link(rank, title) + '</td>'
            + '<td class="px-3 py-2">' + _status_tag(e.get("docling_status")) + '</td>'
            + '<td class="px-3 py-2">' + _status_tag(e.get("grobid_status")) + '</td>'
            + '<td class="px-3 py-2">' + _status_tag(e.get("publisher_xml_status")) + '</td>'
            + '<td class="px-3 py-2 text-xs text-gray-500">' + _val(e.get("preflight_class", "")) + '</td>'
            + '<td class="px-3 py-2">' + (has_qa or _status_tag(e.get("qa_status"))) + '</td>'
            + '<td class="px-3 py-2 text-xs text-gray-500 max-w-xs truncate">' + _val(e.get("notes", ""))[:50] + '</td>'
            + '</tr>')
    h = ('<div class="flex items-center justify-between mb-4"><h2 class="text-lg font-bold text-gray-800">Full-Text Extraction Status</h2>'
        + '<span class="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs font-medium">' + str(len(extractions)) + ' papers</span></div>'
        + '<div class="overflow-x-auto"><table class="w-full text-left"><thead><tr class="border-b border-gray-200 text-xs text-gray-500 uppercase">'
        + '<th class="px-3 py-2 font-medium">Rank</th><th class="px-3 py-2 font-medium">Title</th><th class="px-3 py-2 font-medium">Docling</th>'
        + '<th class="px-3 py-2 font-medium">GROBID</th><th class="px-3 py-2 font-medium">XML</th><th class="px-3 py-2 font-medium">Class</th>'
        + '<th class="px-3 py-2 font-medium">QA</th><th class="px-3 py-2 font-medium">Notes</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
    return HTMLResponse(h)


@router.get("/api/paper/{rank}")
def get_paper(rank: int):
    detail = database.paper_detail(rank)
    if detail is None:
        return HTMLResponse('<p class="text-gray-400 text-center py-8">Paper not found.</p>')

    parts = []

    def kv(label, val):
        if val:
            parts.append(f'<div class="flex justify-between py-1.5 border-b border-gray-100 last:border-0"><span class="text-xs text-gray-500">{label}</span><span class="text-sm text-gray-800 text-right max-w-[60%]">{val}</span></div>')

    title = detail.get("title") or "Unknown"
    parts.append(f'<h2 class="text-lg font-bold text-gray-900 mb-3 leading-snug">{title}</h2>')

    kv("Rank", str(detail.get("rank", "")))
    kv("Decision", _tag(str(detail.get("decision", "")).lower(), COLORS.get(str(detail.get("decision", "")).lower(), "bg-gray-100 text-gray-600")))
    kv("Confidence", _tag(str(detail.get("decision_confidence", "")).lower(), COLORS.get(str(detail.get("decision_confidence", "")).lower(), "bg-gray-100 text-gray-600")))
    kv("Reason Code", str(detail.get("reason_code", "")))
    kv("Reason Note", str(detail.get("reason_note", "")))
    kv("Likely Paper Type", str(detail.get("likely_paper_type", "")))
    kv("Dataset Relationship", str(detail.get("likely_dataset_relationship", "")))
    kv("Named Datasets", str(detail.get("named_datasets", "")))
    kv("Domain", str(detail.get("agricultural_domain", "")))
    kv("Vision Task", str(detail.get("vision_task", "")))
    kv("Modalities", str(detail.get("modalities", "")))

    if "relevance_yes" in detail:
        tags = [t.strip() for t in str(detail.get("relevance_yes", "")).split(";") if t.strip()]
        if tags:
            parts.append('<div class="mt-3"><p class="text-xs text-gray-500 mb-1">Relevance</p><div class="flex flex-wrap gap-1">' + ''.join(f'<span class="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded">{t}</span>' for t in tags) + '</div></div>')

    if detail.get("year") or detail.get("authors") or detail.get("venue"):
        parts.append('<div class="mt-4 pt-3 border-t border-gray-200"><p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Bibliographic</p></div>')
        kv("Year", str(detail.get("year", "")))
        kv("Authors", str(detail.get("authors", "")))
        kv("Venue", str(detail.get("venue", "")))
        kv("DOI", str(detail.get("doi", "")))
        kv("PMID", str(detail.get("pmid", "")))
        kv("Open Access", str(detail.get("is_open_access", "")))

    priority = detail.get("priority")
    if priority:
        parts.append('<div class="mt-4 pt-3 border-t border-gray-200"><p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Priority Scores</p></div>')
        kv("Project Fit", str(priority.get("project_fit", "")))
        kv("Dataset Evidence", str(priority.get("dataset_evidence_value", "")))
        kv("Method Gap", str(priority.get("method_gap_value", "")))
        kv("Decision Leverage", str(priority.get("decision_leverage", "")))
        kv("Actual Use Likelihood", str(priority.get("actual_use_likelihood", "")))
        kv("Info Uncertainty", str(priority.get("information_uncertainty", "")))
        kv("Reading Cost", str(priority.get("estimated_reading_cost", "")))
        kv("Score Confidence", _tag(str(priority.get("score_confidence", "")).lower(), COLORS.get(str(priority.get("score_confidence", "")).lower(), "bg-gray-100 text-gray-600")))
        kv("Primary Role", str(priority.get("primary_role", "")))
        kv("Primary Theme", str(priority.get("primary_theme", "")))
        kv("Evidence Note", str(priority.get("evidence_note", "")))

    extraction = detail.get("extraction")
    if extraction:
        parts.append('<div class="mt-4 pt-3 border-t border-gray-200"><p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Full-Text Extraction</p></div>')
        kv("Docling", _status_tag(extraction.get("docling_status")))
        kv("GROBID", _status_tag(extraction.get("grobid_status")))
        kv("Publisher XML", _status_tag(extraction.get("publisher_xml_status")))
        kv("Preflight Class", str(extraction.get("preflight_class", "")))
        kv("QA Status", str(extraction.get("qa_status", "")))

    artifacts = detail.get("artifacts")
    if artifacts:
        parts.append('<div class="mt-4 pt-3 border-t border-gray-200"><p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Artifacts</p></div>')
        for a in artifacts:
            atype = a.get("artifact_type", "unknown")
            status = a.get("status", "")
            size = a.get("size_bytes", "")
            parts.append(f'<div class="flex justify-between py-1 border-b border-gray-100 text-xs"><span class="text-gray-600">{atype}</span><span class="text-gray-500">{_val(status)} {_val(size) + " bytes" if size else ""}</span></div>')

    kv("Screening ID", str(detail.get("screening_id", "")))
    kv("Reviewer", str(detail.get("reviewer", "")))
    kv("Screened At", str(detail.get("screened_at", "")))
    kv("Batch ID", str(detail.get("batch_id", "")))

    body = "".join(parts)
    html = f'<div class="p-6 overflow-y-auto max-h-screen">{body}</div>'
    return HTMLResponse(html)
