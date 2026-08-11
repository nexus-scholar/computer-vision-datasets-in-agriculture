from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import read_csv

_, ta = read_csv(REPO / "data/curated/screening/title_abstract_decisions_enriched.csv")
_, ft = read_csv(REPO / "data/curated/screening/full_text_decisions.csv")
_, arts = read_csv(REPO / "data/curated/fulltext/artifact_registry.csv")

decided_ft = {r.get("paper_id", "").strip() for r in ft}
fu1 = {r.get("paper_id", "").strip() for r in ft if (r.get("decision") or "").lower() == "unresolved"}
pdf_papers = {r.get("paper_id", "") for r in arts if r.get("status") == "success" and r.get("artifact_type") == "pdf"}

meta = {r.get("candidate_id", "").strip(): r for r in ta}
meta.setdefault("doi:10.1109/lra.2023.3293356", next(r for r in ta if (r.get("candidate_id") or "").strip() == "doi:10.1109/lra.2023.3293356"))
meta.setdefault("titleyear:annotated 3d point cloud dataset of broad leaf legumes captured by high throughput phenotyping platform:",
                next(r for r in ta if (r.get("candidate_id") or "").strip() == "titleyear:annotated 3d point cloud dataset of broad leaf legumes captured by high throughput phenotyping platform:"))
meta.setdefault("titleyear:tomato growth height prediction method by phenotypic feature extraction using multi modal data:",
                next(r for r in ta if (r.get("candidate_id") or "").strip() == "titleyear:tomato growth height prediction method by phenotypic feature extraction using multi modal data:"))

CORRECTIONS = {
    "chong2023ral.pdf": ("doi:10.1109/lra.2023.3293356", "title-match (RA-L 2023 crop-weed segmentation; filename misleading)"),
    "s41597-025-06049-7.pdf": ("titleyear:annotated 3d point cloud dataset of broad leaf legumes captured by high throughput phenotyping platform:",
                               "article is Scientific Data version of Broad-Leaf Legumes 3D point cloud dataset (rank 422)"),
    "j.smartag.SA202410032.pdf": ("titleyear:tomato growth height prediction method by phenotypic feature extraction using multi modal data:",
                                  "Smart Agriculture journal article (rank 528); corpus entry is titleyear id"),
}
FLAGS = {
    "s41597-025-06513-4.pdf": ("PLANTSEG_JOURNAL", "Journal version of PlantSeg (arXiv rank 2 EXCLUDED; zenodo dataset rank 245 included). Article DOI 10.1038/s41597-025-06513-4 not in corpus - needs user decision."),
    "s41597-026-07074-w.pdf": ("NOT_IN_CORPUS", "A Three-Year Multimodal Holistic Dataset For Horticultural Tomato Cultivation (SciData 13:726) not in screening universe - needs user decision."),
}

CONFIRMED_LOW = {
    "2310.11516v2.pdf": "manual-confirmed: arXiv 2310.11516 = 'Field Robot for High-Throughput and High-Resolution 3D Plant Phenotyping' (IEEE RA-M 2023, rank 192)",
    "ECPA23.pdf": "manual-confirmed: 'Automatic estimation of trunk cross sectional area using deep learning' (ECPA 2023, rank 290)",
    "1-s2.0-S0168169919316266-am.pdf": "manual-confirmed: 'Deep Learning Based Segmentation for Automated Training of Apple Trees on Trellis Wires' (Comput. Electron. Agric. 2020, rank 404)",
    "1-s2.0-S0168169923001047-am.pdf": "manual-confirmed: 'Automated Pruning Decisions in Dormant Sweet Cherry Canopies using Instance Segmentation' (Comput. Electron. Agric. 2023, rank 439)",
    "1-s2.0-S2643651525001141-main.pdf": "manual-confirmed: meta_title 'MaizeField3D: A curated 3D point cloud and procedural model dataset...' == corpus rank 450 title",
    "cicba2017a.pdf": "manual-confirmed: meta_title '2017 CICBA Shape-based Fruit Recognition and Classification' == corpus rank 526 title (Jana & Parekh)",
}

matches = json.loads((REPO / "outputs/manual_pdf_matches_v2_20260803.json").read_text(encoding="utf-8"))

plan = []
for m in matches:
    fname = m["file"]
    if fname in CORRECTIONS:
        pid, note = CORRECTIONS[fname]
        rank = meta.get(pid, {}).get("rank", "")
        title = meta.get(pid, {}).get("title", "")
        method = "corrected:" + note
        conf = "high"
    elif fname in FLAGS:
        code, note = FLAGS[fname]
        plan.append({**{k: m.get(k, "") for k in ("file", "pdf_dois", "pdf_arxiv")}, "action": "FLAG", "flag_code": code, "note": note,
                     "matched_paper_id": "", "screening_rank": "", "paper_title": ""})
        continue
    else:
        pid = m.get("matched_paper_id", "")
        rank = m.get("screening_rank", "")
        title = m.get("paper_title", "")
        method = m.get("match_method", "")
        conf = m.get("confidence", "")

    if not pid:
        plan.append({"file": fname, "action": "FLAG", "flag_code": "NO_MATCH", "note": "no corpus match", "matched_paper_id": "", "screening_rank": "", "paper_title": ""})
        continue

    if fname in CONFIRMED_LOW:
        conf = "high"
        method = CONFIRMED_LOW[fname]

    already_pdf = "yes" if pid in pdf_papers else "no"
    if pid in decided_ft and pid not in fu1:
        action = "SKIP_DECIDED"
        note = "full-text decision already exists"
    elif already_pdf == "yes":
        action = "SKIP_HAS_PDF"
        note = "paper already has a PDF artifact"
    elif conf == "low":
        action = "NEEDS_REVIEW"
        note = f"low-confidence match ({method}) - verify before import"
    else:
        action = "IMPORT"
        note = f"match: {method}"

    plan.append({
        "file": fname,
        "pdf_dois": m.get("pdf_dois", ""),
        "pdf_arxiv": m.get("pdf_arxiv", ""),
        "action": action,
        "note": note,
        "confidence": conf,
        "matched_paper_id": pid,
        "screening_rank": rank,
        "paper_title": title,
        "already_has_pdf": already_pdf,
    })

json_out = REPO / "outputs/manual_pdf_import_plan_20260803.json"
json_out.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")

from collections import Counter
print("ACTION COUNTS:", dict(Counter(p["action"] for p in plan)))
print()
for p in plan:
    if p["action"] in ("IMPORT", "NEEDS_REVIEW"):
        print(f"{p['action']:<14} {p['confidence']:<7} {p['file'][:60]:<62} -> {p['matched_paper_id'][:70]} (r{p['screening_rank']})")
print()
print("FLAGS / SKIPS:")
for p in plan:
    if p["action"] not in ("IMPORT", "NEEDS_REVIEW"):
        print(f"{p['action']:<14} {p['file'][:60]:<62} -> {p.get('matched_paper_id','')[:60]} | {p.get('note','')[:80]}")
