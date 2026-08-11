#!/usr/bin/env python3
"""Record batch-7 acquisition failures as unresolved full-text (FU1).

Ranks from FTA_20260803T005806Z manual_resolution_queue that could not be
lawfully acquired: MDPI/Wiley/Taylor&Francis 403 Forbidden, IEEE/IPK/figshare
no_candidate or Crossref 404. Rank 117 was already recorded by
_record_unresolved_117.py; rank 212 was resolved via arXiv and finalized.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(r"C:\Users\mouadh\Documents\Computer Vision Datasets in Agriculture")
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import append_csv, now_utc, sha256_text
from agri_fulltext.schema import FULLTEXT_DECISION_FIELDS
from agri_fulltext.reviewing import DECISIONS, RELATIONSHIPS, ACTUAL_USE, REASON_PREFIXES

TARGET = [
    {"rank": "105", "paper_id": "doi:10.1002/rob.21877",
     "title": "A high-resolution, multimodal data set for agricultural robotics: A Ladybird's-eye view of Brassica"},
    {"rank": "278", "paper_id": "doi:10.3390/s17092007",
     "title": "Novelty Detection Classifiers in Weed Mapping: Silybum marianum Detection on UAV Multispectral Images"},
    {"rank": "78", "paper_id": "doi:10.3390/su17125255",
     "title": "Deep Learning in Multimodal Fusion for Sustainable Plant Care: A Comprehensive Review"},
    {"rank": "106", "paper_id": "doi:10.3390/plants15121912",
     "title": "A Stage-Aware Cascaded Detection-Segmentation Framework for Leaf Phenotyping and Leaf Dry Biomass Estimation of Pepper Seedlings"},
    {"rank": "188", "paper_id": "doi:10.1080/10106049.2024.2440407",
     "title": "EGCM-UNet: Edge Guided Hybrid CNN-Mamba UNet for farmland remote sensing image semantic segmentation"},
    {"rank": "145", "paper_id": "doi:10.6084/m9.figshare.29222462",
     "title": "AgriVision: A Benchmark Dataset for Advancing Real-World Robotic Vision in Densely Fruited Blueberry Crop"},
    {"rank": "114", "paper_id": "doi:10.1109/icra.2017.7989347",
     "title": "UAV-based crop and weed classification for smart farming"},
    {"rank": "184", "paper_id": "doi:10.5447/ipk/2025/14",
     "title": "TomatoMAP_ Tomato Multi-Angle Multi-Pose Dataset for Fine-Grained Phenotyping"},
    {"rank": "109", "paper_id": "doi:10.3390/app10207132",
     "title": "Lightweight Semantic Segmentation Network for Real-Time Weed Mapping Using Unmanned Aerial Vehicles"},
    {"rank": "52", "paper_id": "doi:10.3390/agriculture13071321",
     "title": "Soybean-MVS: Annotated Three-Dimensional Model Dataset of Whole Growth Period Soybeans for 3D Plant Organ Segmentation"},
    {"rank": "62", "paper_id": "doi:10.1109/iccvw69036.2025.00736",
     "title": "AgMIC: Agricultural Masked Image Consistency for Cross-Domain Segmentation"},
    {"rank": "103", "paper_id": "doi:10.1109/cvpr52733.2024.01628",
     "title": "Depth-Aware Concealed Crop Detection in Dense Agricultural Scenes"},
]

FAILURE_NOTES = {
    "doi:10.1002/rob.21877": "Acquisition failed: Wiley full-xml and pdf both HTTP 403 Forbidden (onlinelibrary.wiley.com); no lawful OA copy found via Unpaywall/OpenAlex/S2. Full text unavailable.",
    "doi:10.3390/s17092007": "Acquisition failed: MDPI pdf HTTP 403 Forbidden (mdpi.com/1424-8220/17/9/2007); structured resolver no_candidate. Full text unavailable.",
    "doi:10.3390/su17125255": "Acquisition failed: MDPI pdf HTTP 403 Forbidden (mdpi.com/2071-1050/17/12/5255); structured resolver no_candidate. Full text unavailable.",
    "doi:10.3390/plants15121912": "Acquisition failed: PMC JATS 403, EuropePMC JATS 404, EuropePMC pdf HTTP 500, MDPI pdf 403; no usable artifact. Full text unavailable.",
    "doi:10.1080/10106049.2024.2440407": "Acquisition failed: Taylor & Francis pdf HTTP 403 Forbidden (tandfonline.com); structured resolver no_candidate. Full text unavailable.",
    "doi:10.6084/m9.figshare.29222462": "Acquisition failed: Crossref resolver HTTP 404 (doi 10.6084/m9.figshare.29222462); no PDF/XML candidate (no_candidate). Full text unavailable.",
    "doi:10.1109/icra.2017.7989347": "Acquisition failed: no PDF/XML candidate resolved (IEEE ICRA 2017, paywalled); no lawful OA copy found. Full text unavailable.",
    "doi:10.5447/ipk/2025/14": "Acquisition failed: Crossref resolver HTTP 404 (doi 10.5447/ipk/2025/14); no PDF/XML candidate (no_candidate). Full text unavailable.",
    "doi:10.3390/app10207132": "Acquisition failed: MDPI pdf HTTP 403 Forbidden (mdpi.com/2076-3417/10/20/7132); structured resolver no_candidate. Full text unavailable.",
    "doi:10.3390/agriculture13071321": "Acquisition failed: MDPI pdf HTTP 403 Forbidden (mdpi.com/2077-0472/13/7/1321); structured resolver no_candidate. Full text unavailable.",
    "doi:10.1109/iccvw69036.2025.00736": "Acquisition failed: no PDF/XML candidate resolved (IEEE ICCV Workshop 2025, paywalled); no lawful OA copy found. Full text unavailable.",
    "doi:10.1109/cvpr52733.2024.01628": "Acquisition failed: no PDF/XML candidate resolved (IEEE CVPR 2024, paywalled); no lawful OA copy found. Full text unavailable.",
}


def main() -> int:
    decisions_path = REPO / "data/curated/screening/full_text_decisions.csv"
    import csv

    with decisions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        existing = [dict(row) for row in reader]

    existing_paper_ids = {row.get("paper_id", "") for row in existing}
    existing_ranks = {row.get("rank", "") for row in existing}

    ts = now_utc()
    rows = []
    for meta in TARGET:
        if meta["paper_id"] in existing_paper_ids or meta["rank"] in existing_ranks:
            raise SystemExit(
                f"Refusing: paper/rank already has a full-text decision "
                f"({meta['rank']} {meta['paper_id']})"
            )
        row = {field: "" for field in FULLTEXT_DECISION_FIELDS}
        row.update(
            {
                "fulltext_screening_id": "FTS_" + sha256_text(f"{meta['paper_id']}||{ts}|unresolved")[:20],
                "paper_id": meta["paper_id"],
                "rank": meta["rank"],
                "title": meta["title"],
                "extraction_id": "",
                "decision": "unresolved",
                "reason_code": "FU1_FULLTEXT_UNAVAILABLE",
                "paper_role": "unclear",
                "actual_dataset_use": "unclear",
                "dataset_relationship": "unclear",
                "named_datasets": "unknown",
                "evidence_summary": "No full-text artifact acquirable (paywalled or unresolved DOI; all legal resolver sources exhausted). Full-text screening cannot be performed; paper remains unresolved pending lawful access.",
                "source_page": "unknown",
                "source_section": "unknown",
                "source_table": "unknown",
                "source_figure": "unknown",
                "reviewer": "opencode_ai",
                "reviewed_at": ts,
                "supersedes_fulltext_screening_id": "",
                "notes": FAILURE_NOTES[meta["paper_id"]]
                + " See outputs/fulltext/acquisition/FTA_20260803T005806Z/manual_resolution_queue.csv.",
            }
        )
        if row["decision"] not in DECISIONS:
            raise SystemExit("bad decision")
        if not row["reason_code"].startswith(REASON_PREFIXES["unresolved"][0]):
            raise SystemExit("bad reason prefix")
        if row["actual_dataset_use"] not in ACTUAL_USE:
            raise SystemExit("bad actual_dataset_use")
        if row["dataset_relationship"] not in RELATIONSHIPS:
            raise SystemExit("bad relationship")
        rows.append(row)

    append_csv(decisions_path, FULLTEXT_DECISION_FIELDS, rows)
    print(f"Appended {len(rows)} unresolved decisions to {decisions_path}")
    for row in rows:
        print(row["rank"], row["fulltext_screening_id"], row["paper_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
