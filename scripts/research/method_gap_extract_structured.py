#!/usr/bin/env python3
"""Phase 1: extract structured data from extraction_registry and QA outputs.
Produces outputs/method_gap_matrix.csv with ~32 columns (6 tag columns empty)."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools/fulltext_pipeline" / "src"))

from agri_fulltext.io_utils import read_csv, atomic_write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repository root")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    _, decisions = read_csv(repo / "data/curated/screening/full_text_decisions.csv")
    _, registry = read_csv(repo / "data/curated/fulltext/extraction_registry.csv")

    # Latest extraction per paper_id
    latest = {}
    for r in registry:
        pid = r.get("paper_id", "")
        if pid not in latest or r.get("created_at", "") >= latest[pid].get("created_at", ""):
            latest[pid] = r

    included = [x for x in decisions if x["decision"] in ("include_core", "include_supporting")]
    print(f"Included papers: {len(included)}")

    fields = [
        "rank", "paper_id", "title", "decision", "year", "authors", "venue",
        "doi", "arxiv_id",
        "sources", "has_pdf", "has_xml", "rights_status",
        "preflight_class", "page_count", "has_ocr_recommendation",
        "docling_status", "grobid_status", "publisher_xml_status",
        "docling_file_count", "docling_markdown_chars", "docling_chunk_count",
        "docling_table_count", "docling_figure_count", "docling_formula_count",
        "grobid_tei_size", "publisher_markdown_chars",
        "qa_status", "qa_text_quality", "qa_layout_quality",
        "qa_table_quality", "qa_figure_quality", "qa_page_grounding",
        "needs_visual_review",
        "split_level", "baseline_strength", "calibration_reported",
        "cross_sensor_test", "code_available", "dataset_role",
        "confidence_notes",
    ]

    _, artifacts = read_csv(repo / "data/curated/fulltext/artifact_registry.csv")

    rows = []
    seen_ids = set()
    for dec in included:
        pid = dec.get("paper_id", "")
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        ext = latest.get(pid, {})
        od = ext.get("output_dir", "")

        paper_artifacts = [a for a in artifacts if a.get("paper_id") == pid]
        has_pdf = any(
            a.get("artifact_type") == "pdf" and a.get("status") == "success"
            for a in paper_artifacts
        )
        has_xml = any(
            a.get("artifact_type") in ("jats_xml", "tei_xml", "xml")
            and a.get("status") == "success"
            for a in paper_artifacts
        )
        sources = set(a.get("source", "") for a in paper_artifacts if a.get("source"))
        rights = set(
            a.get("rights_status", "") for a in paper_artifacts if a.get("rights_status")
        )

        out_dir = repo / od if od else None
        manifest_data = {}
        preflight_data = {}
        qa_data = {}
        grobid_tei = 0
        publisher_chars = 0

        if out_dir:
            mf = out_dir / "manifest.json"
            if mf.exists():
                manifest_data = json.loads(mf.read_text(encoding="utf-8"))
            pf = out_dir / "qa" / "preflight.json"
            if pf.exists():
                preflight_data = json.loads(pf.read_text(encoding="utf-8"))
            qf = out_dir / "qa" / "extraction_quality.json"
            if qf.exists():
                qa_data = json.loads(qf.read_text(encoding="utf-8"))
            gt = out_dir / "grobid" / "fulltext.tei.xml"
            if gt.exists():
                grobid_tei = gt.stat().st_size
            pfd = out_dir / "publisher_xml" / "document.md"
            if pfd.exists():
                publisher_chars = pfd.stat().st_size

        docling = manifest_data.get("docling", {})

        rows.append({
            "rank": dec.get("rank", ""),
            "paper_id": pid,
            "title": dec.get("title", ""),
            "decision": dec.get("decision", ""),
            "year": dec.get("year", ""),
            "authors": str(dec.get("authors", ""))[:80],
            "venue": dec.get("venue", ""),
            "doi": dec.get("doi", ""),
            "arxiv_id": dec.get("arxiv_id", ""),
            "sources": ";".join(sources),
            "has_pdf": "yes" if has_pdf else "no",
            "has_xml": "yes" if has_xml else "no",
            "rights_status": ";".join(rights),
            "preflight_class": preflight_data.get("classification", ""),
            "page_count": str(preflight_data.get("page_count", "")),
            "has_ocr_recommendation": "yes" if preflight_data.get("recommended_ocr") else "no",
            "docling_status": ext.get("docling_status", ""),
            "grobid_status": ext.get("grobid_status", ""),
            "publisher_xml_status": ext.get("publisher_xml_status", ""),
            "docling_file_count": docling.get("file_count", ""),
            "docling_markdown_chars": docling.get("markdown_chars", ""),
            "docling_chunk_count": docling.get("chunk_count", ""),
            "docling_table_count": docling.get("table_count", ""),
            "docling_figure_count": docling.get("figure_count", ""),
            "docling_formula_count": docling.get("formula_count", ""),
            "grobid_tei_size": grobid_tei,
            "publisher_markdown_chars": publisher_chars,
            "qa_status": ext.get("qa_status", ""),
            "qa_text_quality": qa_data.get("text_quality", ""),
            "qa_layout_quality": qa_data.get("layout_quality", ""),
            "qa_table_quality": qa_data.get("table_quality", ""),
            "qa_figure_quality": qa_data.get("figure_quality", ""),
            "qa_page_grounding": qa_data.get("page_grounding_quality", ""),
            "needs_visual_review": qa_data.get("needs_visual_review", ""),
            "split_level": "",
            "baseline_strength": "",
            "calibration_reported": "",
            "cross_sensor_test": "",
            "code_available": "",
            "dataset_role": "",
            "confidence_notes": "",
        })

    out_path = repo / "outputs" / "method_gap_matrix.csv"
    atomic_write_csv(out_path, fields, rows)
    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Deduplicated paper_ids: {len(seen_ids)}")

    # Quick stats
    print(f"\nHas PDF: {sum(1 for r in rows if r['has_pdf']=='yes')}/{len(rows)}")
    print(f"Docling success: {sum(1 for r in rows if r['docling_status']=='success')}/{len(rows)}")
    print(f"QA statuses: {dict(Counter(r['qa_status'] for r in rows))}")
    print(f"\nPhase 1 complete. Run Phase 2 (evidence extraction + tagging) to fill the 6 method dimensions.")


if __name__ == "__main__":
    main()
