#!/usr/bin/env python3
"""Record batch-7 rank 117 as unresolved full-text (coredata-only Elsevier stub)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(r"C:\Users\mouadh\Documents\Computer Vision Datasets in Agriculture")
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.io_utils import append_csv, now_utc, sha256_text
from agri_fulltext.schema import FULLTEXT_DECISION_FIELDS
from agri_fulltext.reviewing import DECISIONS, RELATIONSHIPS, ACTUAL_USE, REASON_PREFIXES

TARGET = {
    "rank": "117",
    "paper_id": "doi:10.1016/j.jksuci.2023.03.023",
    "title": "Multi-level feature re-weighted fusion for the semantic segmentation of crops and weeds",
}

FAILURE_NOTE = (
    "Acquisition resolved only an Elsevier coredata XML stub (1,999 bytes, metadata only, "
    "no article body); Semantic Scholar PDF candidate returned non-PDF content "
    "(ValueError: Artifact is neither a valid PDF nor well-formed XML); no lawful full-text "
    "copy obtainable. Extraction failed: insufficient extracted text or chunks. "
    "See outputs/fulltext/acquisition/FTA_20260803T005806Z/manual_resolution_queue.csv."
)


def main() -> int:
    decisions_path = REPO / "data/curated/screening/full_text_decisions.csv"
    import csv

    with decisions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        existing = [dict(row) for row in reader]

    existing_paper_ids = {row.get("paper_id", "") for row in existing}
    existing_ranks = {row.get("rank", "") for row in existing}

    if TARGET["paper_id"] in existing_paper_ids or TARGET["rank"] in existing_ranks:
        raise SystemExit(
            f"Refusing: paper/rank already has a full-text decision "
            f"({TARGET['rank']} {TARGET['paper_id']})"
        )

    ts = now_utc()
    row = {field: "" for field in FULLTEXT_DECISION_FIELDS}
    row.update(
        {
            "fulltext_screening_id": "FTS_" + sha256_text(f"{TARGET['paper_id']}||{ts}|unresolved")[:20],
            "paper_id": TARGET["paper_id"],
            "rank": TARGET["rank"],
            "title": TARGET["title"],
            "extraction_id": "",
            "decision": "unresolved",
            "reason_code": "FU1_FULLTEXT_UNAVAILABLE",
            "paper_role": "unclear",
            "actual_dataset_use": "unclear",
            "dataset_relationship": "unclear",
            "named_datasets": "unknown",
            "evidence_summary": "No usable full-text artifact acquirable (coredata-only XML stub; PDF candidate invalid). Full-text screening cannot be performed; paper remains unresolved pending lawful access.",
            "source_page": "unknown",
            "source_section": "unknown",
            "source_table": "unknown",
            "source_figure": "unknown",
            "reviewer": "opencode_ai",
            "reviewed_at": ts,
            "supersedes_fulltext_screening_id": "",
            "notes": FAILURE_NOTE,
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

    append_csv(decisions_path, FULLTEXT_DECISION_FIELDS, [row])
    print(f"Appended unresolved decision to {decisions_path}")
    print(row["rank"], row["fulltext_screening_id"], row["paper_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
