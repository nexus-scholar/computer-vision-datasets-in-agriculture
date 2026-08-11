"""Deterministic recording event: dispose of the 35 reconciliation ranks that
remain after the rank-184 (TomatoMAP) full-text review was finalized.

Categories recorded here:
  * 8 DUP ranks (63,333,339,378,408,447,390,463) -> exclude FE05_DUPLICATE,
    each pointing at the FTS id of its already-decided twin (same work).
  * 28 ranks without a usable full-text artifact -> unresolved
    FU1_FULLTEXT_UNAVAILABLE. 19 are ordinary papers whose lawful acquisition
    was exhausted; 8 are standalone dataset records (Pl@ntNet-300K, AgRobTomato,
    Mendeley/Kaggle/Zenodo records) with no companion article in the corpus;
    rank 245 is the Zenodo PlantSeg dataset record whose companion SciData
    article is out of corpus (arXiv preprint was excluded E05_DUPLICATE).

These decisions are AI-provisional and require human confirmation
(dataset selection / manuscript claims per AGENTS.md).

This script never overwrites existing rows; it asserts no prior decision exists
for any of the 35 papers and appends deterministic FTS ids.
"""

from pathlib import Path
from typing import Any

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import append_csv, now_utc, read_csv, sha256_text
from agri_fulltext.schema import FULLTEXT_DECISION_FIELDS

REVIEWER = "opencode_ai"
REASON_FU1 = "FU1_FULLTEXT_UNAVAILABLE"
REASON_DUP = "FE05_DUPLICATE"

# rank -> (paper_id, twin_rank, twin_fts_id, twin_decision)
DUP_TARGETS = [
    (63, "doi:10.6084/m9.figshare.28270742", 422, "FTS_c5309834ec188e73f634", "include_core"),
    (333, "titleyear:tomatowur an annotated dataset of 3d tomato plants to quantitatively evaluate segmentation skeletonisation and plant trait extraction algorithms for 3d plant phenotyping 2025 4tu:", 68, "FTS_28cf141e4c5d16eb89a4", "include_core"),
    (339, "doi:10.14459/2023mp1717366", 1, "FTS_f0946f19ad81e8edb3b9", "include_core"),
    (378, "doi:10.1007/978-3-031-91835-3_4", 44, "FTS_643d13c3e63a0573bd07", "include_core"),
    (408, "titleyear:last straw lincoln s annotated spatio temporal strawberry dataset:2025", 44, "FTS_643d13c3e63a0573bd07", "include_core"),
    (447, "titleyear:a leaf level dataset for soybean cotton detection and segmentation 2025:", 5, "FTS_00da5c38aa34d4c4d8ff", "include_core"),
    (390, "titleyear:tomatopgt tools binary release cloudseg and cloudgraph for organ level digital twin modeling of tomato plants from 3d point clouds:2026", 42, "FTS_663709bebe688630cf7b", "include_core"),
    (463, "titleyear:tomato multi angle multi pose dataset for fine grained phenotyping:", 184, "FTS_639cf9461904678ed830", "include_core"),
]

# paper ranks whose lawful acquisition was exhausted; plain papers.
PAPER_FU1_RANKS = [
    56, 120, 135, 158, 167, 169, 182, 263, 319, 337,
    343, 351, 354, 421, 457, 474, 505, 516, 549,
]

# standalone dataset records with no companion article in the corpus.
DS_FU1_RANKS = [144, 379, 409, 460, 461, 504, 520, 521]

# PlantSeg Zenodo record; companion SciData article out of corpus.
PLANTSEG_RANKS = [245]

FU1_NOTE_PAPER = (
    "Lawful acquisition exhausted (no_candidate/skipped_rights across direct/PMC/"
    "EuropePMC/arXiv/Unpaywall/Crossref/OpenAlex/S2 resolvers); no artifact "
    "registered (outputs/fulltext/acquisition/FTA_* manual_resolution_queue.csv). "
    "Full text unavailable; recorded unresolved FU1_FULLTEXT_UNAVAILABLE during "
    "2026-08-08 reconciliation; AI-provisional, needs human confirmation."
)

FU1_NOTE_DS = (
    "Standalone dataset record (no in-corpus companion article): this candidate "
    "is the dataset artifact itself (Zenodo/Mendeley/Kaggle/titleyear record), "
    "not a paper; no lawful full-text article obtainable and no companion article "
    "is in the corpus. Full-text screening of a paper cannot be performed; "
    "recorded unresolved FU1_FULLTEXT_UNAVAILABLE during 2026-08-08 reconciliation; "
    "dataset-registry inclusion pending human confirmation."
)

FU1_NOTE_PLANTSEG = (
    "Zenodo dataset record (10.5281/zenodo.17719108) of the PlantSeg dataset. Its "
    "companion Scientific Data article (10.1038/s41597-025-06513-4) is NOT in the "
    "corpus; the arXiv preprint (rank 2) was excluded at TA stage as "
    "E05_DUPLICATE of that article. Full-text screening of a paper cannot be "
    "performed from this record; recorded unresolved FU1_FULLTEXT_UNAVAILABLE "
    "during 2026-08-08 reconciliation; dataset-registry inclusion (PlantSeg is a "
    "real large-scale in-the-wild disease-segmentation dataset) pending human "
    "confirmation."
)


def dup_note(rank: int, paper_id: str, twin_rank: int, twin_fts: str, twin_decision: str) -> str:
    return (
        f"duplicate_of:rank {twin_rank} (FTS {twin_fts}, {twin_decision}); same work "
        f"as an already-decided paper — recorded FE05_DUPLICATE during 2026-08-08 "
        f"reconciliation ({paper_id}); scientific content covered by the twin "
        f"decision; AI-provisional, needs human confirmation."
    )


def dup_evidence(rank: int, twin_rank: int, twin_fts: str) -> str:
    return (
        f"Strict duplicate of rank {twin_rank} (FTS {twin_fts}): identical dataset/"
        f"work already fully screened at the full-text stage. Recorded exclude "
        f"FE05_DUPLICATE so this corpus row is disposed without an independent "
        f"review; the twin decision is the authoritative evidence."
    )


def main() -> None:
    settings = load_settings(Path(__file__).resolve().parents[2])
    decisions_path = Path(settings.repo / "data/curated/screening/full_text_decisions.csv")
    _, existing = read_csv(decisions_path)
    by_paper = {row.get("paper_id", ""): row for row in existing}

    ta_path = Path(settings.repo / "data/curated/screening/title_abstract_decisions.csv")
    _, ta_rows = read_csv(ta_path)
    ta_by_rank = {int(row.get("rank", "0")): row for row in ta_rows if row.get("rank", "").strip()}

    reviewed_at = now_utc()
    rows: list[dict[str, Any]] = []

    for rank, paper_id, twin_rank, twin_fts, twin_decision in DUP_TARGETS:
        _assert_no_decision(by_paper, rank, paper_id)
        ta = ta_by_rank[rank]
        if ta.get("candidate_id", "") != paper_id:
            raise SystemExit(f"ABORT: TA paper_id mismatch for rank {rank}: {ta.get('candidate_id')} != {paper_id}")
        fts_id = "FTS_" + sha256_text(f"{paper_id}||{reviewed_at}|exclude")[:20]
        rows.append(
            {
                "fulltext_screening_id": fts_id,
                "paper_id": paper_id,
                "rank": rank,
                "title": ta.get("title", ""),
                "extraction_id": "",
                "decision": "exclude",
                "reason_code": REASON_DUP,
                "paper_role": ta.get("likely_paper_type", "dataset_paper") or "dataset_paper",
                "actual_dataset_use": "no",
                "dataset_relationship": "unclear",
                "named_datasets": "unknown",
                "evidence_summary": dup_evidence(rank, twin_rank, twin_fts),
                "source_page": "unknown",
                "source_section": "unknown",
                "source_table": "unknown",
                "source_figure": "unknown",
                "reviewer": REVIEWER,
                "reviewed_at": reviewed_at,
                "supersedes_fulltext_screening_id": "",
                "notes": dup_note(rank, paper_id, twin_rank, twin_fts, twin_decision),
            }
        )

    for rank, note in [(r, FU1_NOTE_PAPER) for r in PAPER_FU1_RANKS] + [
        (r, FU1_NOTE_DS) for r in DS_FU1_RANKS
    ] + [(r, FU1_NOTE_PLANTSEG) for r in PLANTSEG_RANKS]:
        ta = ta_by_rank[rank]
        paper_id = ta.get("candidate_id", "")
        _assert_no_decision(by_paper, rank, paper_id)
        fts_id = "FTS_" + sha256_text(f"{paper_id}||{reviewed_at}|unresolved")[:20]
        rows.append(
            {
                "fulltext_screening_id": fts_id,
                "paper_id": paper_id,
                "rank": rank,
                "title": ta.get("title", ""),
                "extraction_id": "",
                "decision": "unresolved",
                "reason_code": REASON_FU1,
                "paper_role": "unclear",
                "actual_dataset_use": "unclear",
                "dataset_relationship": "unclear",
                "named_datasets": "unknown",
                "evidence_summary": (
                    "No full-text artifact with usable article body acquirable; "
                    "all legal resolver sources exhausted. Full-text screening "
                    "cannot be performed; paper remains unresolved pending lawful "
                    "access."
                ),
                "source_page": "unknown",
                "source_section": "unknown",
                "source_table": "unknown",
                "source_figure": "unknown",
                "reviewer": REVIEWER,
                "reviewed_at": reviewed_at,
                "supersedes_fulltext_screening_id": "",
                "notes": note,
            }
        )

    existing_ids = {row.get("fulltext_screening_id", "") for row in existing}
    duplicates = [r["fulltext_screening_id"] for r in rows if r["fulltext_screening_id"] in existing_ids]
    if duplicates:
        raise SystemExit(f"ABORT: duplicate FTS ids would be created: {duplicates}")

    append_csv(decisions_path, FULLTEXT_DECISION_FIELDS, rows)
    print(f"recorded {len(rows)} reconciliation decisions (8 exclude FE05_DUPLICATE, "
          f"{len(PAPER_FU1_RANKS)} paper FU1, {len(DS_FU1_RANKS)} dataset-record FU1, "
          f"{len(PLANTSEG_RANKS)} PlantSeg FU1):")
    for r in rows:
        print(f"  {r['fulltext_screening_id']}  rank {r['rank']}  {r['decision']}  {r['reason_code']}  {r['paper_id']}")


def _assert_no_decision(by_paper: dict[str, dict[str, Any]], rank: int, paper_id: str) -> None:
    if paper_id in by_paper:
        raise SystemExit(
            f"ABORT: {paper_id} (rank {rank}) already has a decision "
            f"{by_paper[paper_id].get('fulltext_screening_id')}; refusing to record without supersession."
        )


if __name__ == "__main__":
    main()
