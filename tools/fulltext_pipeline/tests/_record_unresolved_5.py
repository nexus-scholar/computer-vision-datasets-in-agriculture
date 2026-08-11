#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(r"C:\Users\mouadh\Documents\Computer Vision Datasets in Agriculture")
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import append_csv, now_utc, sha256_text
from agri_fulltext.schema import FULLTEXT_DECISION_FIELDS
from agri_fulltext.reviewing import DECISIONS, RELATIONSHIPS, ACTUAL_USE, REASON_PREFIXES

TARGET = [
    {
        "rank": "13",
        "paper_id": "doi:10.1002/ps.70881",
        "title": "ASVLB-Net: A lightweight network for multispectral weed segmentation with NDVI-guided adaptive fusion",
    },
    {
        "rank": "23",
        "paper_id": "doi:10.1109/tgrs.2026.3690653",
        "title": "RPD: Learning Efficient Crops and Weeds for Field Semantic Segmentation in Drone Images",
    },
    {
        "rank": "26",
        "paper_id": "doi:10.1109/cict67193.2025.11399080",
        "title": "AgriSeg: A Comprehensive Study on Semantic Segmentation for Leaf Disease, Fruit, and Crop-Weed Detection",
    },
    {
        "rank": "32",
        "paper_id": "doi:10.1109/incet64471.2025.11140034",
        "title": "An Efficient Weed Detection Model using RCNN and YOLO Algorithms",
    },
    {
        "rank": "40",
        "paper_id": "doi:10.1109/itechsecom64750.2025.11307551",
        "title": "Weed and Crop Detection Using YOLOv7: A Step Toward Smarter Precision Agriculture",
    },
]

FAILURE_NOTES = {
    "doi:10.1002/ps.70881": "Acquisition failed: crossref pdf/xml both HTTP 403 Forbidden (Wiley scijournals.onlinelibrary); no lawful OA copy found via Unpaywall/OpenAlex/S2; no author copy obtainable. Full text unavailable.",
    "doi:10.1109/tgrs.2026.3690653": "Acquisition failed: no PDF/xml candidate resolved (IEEE TGRS, paywalled); no lawful OA copy found. Full text unavailable.",
    "doi:10.1109/cict67193.2025.11399080": "Acquisition failed: no PDF/xml candidate resolved (IEEE CICT 2025, paywalled); no lawful OA copy found. Full text unavailable.",
    "doi:10.1109/incet64471.2025.11140034": "Acquisition failed: no PDF/xml candidate resolved (IEEE INCET 2025, paywalled); no lawful OA copy found. Full text unavailable.",
    "doi:10.1109/itechsecom64750.2025.11307551": "Acquisition failed: no PDF/xml candidate resolved (IEEE iTechSECOM 2025, paywalled); no lawful OA copy found. Full text unavailable.",
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
                "evidence_summary": "No full-text artifact acquirable (paywalled; all legal resolver sources exhausted). Full-text screening cannot be performed; paper remains unresolved pending lawful access.",
                "source_page": "unknown",
                "source_section": "unknown",
                "source_table": "unknown",
                "source_figure": "unknown",
                "reviewer": "opencode_ai",
                "reviewed_at": ts,
                "supersedes_fulltext_screening_id": "",
                "notes": FAILURE_NOTES[meta["paper_id"]]
                + " See outputs/fulltext/acquisition/FTA_20260731T121706Z/manual_resolution_queue.csv.",
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
