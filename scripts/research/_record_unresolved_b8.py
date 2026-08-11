"""Deterministic recording event: mark 13 content-level-unprocessable papers as
unresolved (FU1_FULLTEXT_UNAVAILABLE) in full_text_decisions.csv.

These papers have an artifact registered (Elsevier coredata stub XML for ranks
218/244/280/341/364/370/405/434/451/471/496/511; 1-page stub PDF for rank 372)
but the artifact contains no usable article body. A final audited re-acquisition
(FTA_20260808T001722Z) returned pdf_result=no_candidate for all 13, so no lawful
full-text copy is obtainable through the configured resolvers.

This script never overwrites existing rows; it asserts no prior decision exists
for any of the 13 papers and appends one unresolved row per paper with a
deterministic FTS id (matching the finalize-review scheme).
"""

from pathlib import Path
from typing import Any

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import append_csv, now_utc, read_csv, sha256_text
from agri_fulltext.schema import FULLTEXT_DECISION_FIELDS

TARGETS = [
    ("doi:10.1016/j.compag.2025.111167", 218, "stub_xml"),
    ("doi:10.1016/j.compag.2019.02.005", 244, "stub_xml"),
    ("doi:10.1016/j.asoc.2020.106597", 280, "stub_xml"),
    ("doi:10.1016/j.compag.2019.105091", 341, "stub_xml"),
    ("doi:10.1016/j.compag.2018.05.012", 364, "stub_xml"),
    ("doi:10.1016/j.eswa.2012.03.040", 370, "stub_xml"),
    ("doi:10.1016/j.asoc.2015.08.027", 372, "stub_pdf"),
    ("doi:10.1016/j.compag.2024.109201", 405, "stub_xml"),
    ("doi:10.1016/j.compag.2017.12.032", 434, "stub_xml"),
    ("doi:10.1016/j.compag.2021.106468", 451, "stub_xml"),
    ("doi:10.1016/j.compag.2022.107345", 471, "stub_xml"),
    ("doi:10.1016/0034-4257(95)00186-7", 496, "stub_xml"),
    ("doi:10.1016/j.compag.2019.06.001", 511, "stub_xml"),
]

REVIEWER = "opencode_ai"
REASON = "FU1_FULLTEXT_UNAVAILABLE"


def note_for(kind: str) -> str:
    if kind == "stub_pdf":
        return (
            "Only lawful artifact is a 1-page stub PDF from Semantic Scholar "
            "(373 chars, no article body). Re-acquisition FTA_20260808T001722Z "
            "returned pdf_result=no_candidate across all resolvers (direct/PMC/"
            "EuropePMC/arXiv/Unpaywall/Crossref/OpenAlex/S2). Full text unavailable."
        )
    return (
        "Only lawful artifact is an Elsevier coredata stub (full-text-retrieval-"
        "response, ~1.8 KB, metadata only, no article body) from Crossref TDM. "
        "Re-acquisition FTA_20260808T001722Z returned pdf_result=no_candidate "
        "across all resolvers (direct/PMC/EuropePMC/arXiv/Unpaywall/Crossref/"
        "OpenAlex/S2). Full text unavailable."
    )


def main() -> None:
    settings = load_settings(Path(__file__).resolve().parents[2])
    decisions_path = Path(settings.repo / "data/curated/screening/full_text_decisions.csv")
    _, existing = read_csv(decisions_path)
    by_paper = {row.get("paper_id", ""): row for row in existing}

    summary_path = settings.repo / "outputs/fulltext/acquisition/FTA_20260808T001722Z/summary.csv"
    _, summary = read_csv(summary_path)
    title_by_paper = {row.get("paper_id", ""): row.get("title", "") for row in summary}

    reviewed_at = now_utc()
    rows: list[dict[str, Any]] = []
    for paper_id, rank, kind in TARGETS:
        if paper_id in by_paper:
            raise SystemExit(
                f"ABORT: {paper_id} (rank {rank}) already has a decision "
                f"{by_paper[paper_id].get('fulltext_screening_id')}; refusing to record without supersession."
            )
        fts_id = "FTS_" + sha256_text(f"{paper_id}||{reviewed_at}|unresolved")[:20]
        rows.append(
            {
                "fulltext_screening_id": fts_id,
                "paper_id": paper_id,
                "rank": rank,
                "title": title_by_paper.get(paper_id, ""),
                "extraction_id": "",
                "decision": "unresolved",
                "reason_code": REASON,
                "paper_role": "unclear",
                "actual_dataset_use": "unclear",
                "dataset_relationship": "unclear",
                "named_datasets": "unknown",
                "evidence_summary": (
                    "No full-text artifact with usable article body acquirable "
                    "(only Elsevier coredata stub / stub PDF; all legal resolver "
                    "sources exhausted). Full-text screening cannot be performed; "
                    "paper remains unresolved pending lawful access."
                ),
                "source_page": "unknown",
                "source_section": "unknown",
                "source_table": "unknown",
                "source_figure": "unknown",
                "reviewer": REVIEWER,
                "reviewed_at": reviewed_at,
                "supersedes_fulltext_screening_id": "",
                "notes": note_for(kind),
            }
        )

    existing_ids = {row.get("fulltext_screening_id", "") for row in existing}
    duplicates = [r["fulltext_screening_id"] for r in rows if r["fulltext_screening_id"] in existing_ids]
    if duplicates:
        raise SystemExit(f"ABORT: duplicate FTS ids would be created: {duplicates}")

    append_csv(decisions_path, FULLTEXT_DECISION_FIELDS, rows)
    print(f"recorded {len(rows)} unresolved decisions (FU1_FULLTEXT_UNAVAILABLE):")
    for r in rows:
        print(f"  {r['fulltext_screening_id']}  rank {r['rank']}  {r['paper_id']}")


if __name__ == "__main__":
    main()
