import re
import subprocess
import sys
from pathlib import Path

import pytest

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import append_csv, atomic_write_csv, read_csv, read_json
from agri_fulltext.queueing import QueueValidationError, build_queue, build_queue_from_ranking, load_eligible_works


RANKING_FIELDS = [
    "candidate_id", "original_screening_rank", "recommended_fulltext_rank",
    "title", "year", "authors", "venue", "doi", "arxiv_id", "pmid", "pmcid",
    "paper_id", "canonical_paper_id",
    "landing_url", "pdf_url", "is_open_access", "provider_ids", "priority_score",
    "likely_paper_type",
]


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    queue = repo / "outputs/screening_queue_2026-07-22/screening_queue.csv"
    decisions = repo / "data/curated/screening/title_abstract_decisions_enriched.csv"
    atomic_write_csv(queue, [
        "screening_rank", "canonical_paper_id", "title", "year", "authors", "venue", "doi", "arxiv_id",
        "pmid", "pmcid", "landing_url", "pdf_url", "is_open_access", "provider_ids", "priority_score",
    ], [{
        "screening_rank": "1", "canonical_paper_id": "doi:10.1/test", "title": "Test paper", "year": "2025",
        "authors": "A", "venue": "V", "doi": "10.1/test", "arxiv_id": "", "pmid": "", "pmcid": "123",
        "landing_url": "https://example.org", "pdf_url": "https://example.org/test.pdf", "is_open_access": "True",
        "provider_ids": "openalex:W1; semantic_scholar:S1", "priority_score": "9",
    }])
    atomic_write_csv(decisions, [
        "candidate_id", "rank", "title", "decision", "decision_confidence", "likely_paper_type", "provider_ids",
    ], [{
        "candidate_id": "doi:10.1/test", "rank": "1", "title": "Test paper", "decision": "include",
        "decision_confidence": "high", "likely_paper_type": "dataset_paper",
        "provider_ids": "openalex:W1; semantic_scholar:S1",
    }])
    return repo


def make_ranking_repo(tmp_path: Path, decisions_rows: list[dict[str, str]] | None = None) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    queue = repo / "outputs/screening_queue_2026-07-22/screening_queue.csv"
    decisions = repo / "data/curated/screening/title_abstract_decisions_enriched.csv"
    artifact = repo / "data/curated/fulltext/artifact_registry.csv"

    atomic_write_csv(queue, [
        "screening_rank", "canonical_paper_id", "title", "year", "authors", "venue", "doi", "arxiv_id",
        "pmid", "pmcid", "landing_url", "pdf_url", "is_open_access", "provider_ids", "priority_score",
    ], [
        {"screening_rank": "1", "canonical_paper_id": "doi:10.1/a", "title": "Paper A", "year": "2024",
         "authors": "Author A", "venue": "Venue A", "doi": "10.1/a", "arxiv_id": "", "pmid": "",
         "pmcid": "PMC1", "landing_url": "https://a.org", "pdf_url": "https://a.org/a.pdf",
         "is_open_access": "True", "provider_ids": "openalex:WA1", "priority_score": "8"},
        {"screening_rank": "2", "canonical_paper_id": "doi:10.1/b", "title": "Paper B", "year": "2023",
         "authors": "Author B", "venue": "Venue B", "doi": "10.1/b", "arxiv_id": "", "pmid": "",
         "pmcid": "PMC2", "landing_url": "https://b.org", "pdf_url": "https://b.org/b.pdf",
         "is_open_access": "True", "provider_ids": "openalex:WB1", "priority_score": "7"},
        {"screening_rank": "3", "canonical_paper_id": "doi:10.1/c", "title": "Paper C", "year": "2022",
         "authors": "Author C", "venue": "Venue C", "doi": "10.1/c", "arxiv_id": "", "pmid": "",
         "pmcid": "PMC3", "landing_url": "https://c.org", "pdf_url": "", "is_open_access": "False",
         "provider_ids": "openalex:WC1", "priority_score": "6"},
    ])

    if decisions_rows is None:
        decisions_rows = [
            {"candidate_id": "doi:10.1/a", "rank": "1", "title": "Paper A",
             "decision": "include", "decision_confidence": "high", "likely_paper_type": "dataset_paper",
             "provider_ids": "openalex:WA1", "doi": "10.1/a", "year": "2024"},
            {"candidate_id": "doi:10.1/b", "rank": "2", "title": "Paper B",
             "decision": "include", "decision_confidence": "medium", "likely_paper_type": "method_paper",
             "provider_ids": "openalex:WB1", "doi": "10.1/b", "year": "2023"},
            {"candidate_id": "doi:10.1/c", "rank": "3", "title": "Paper C",
             "decision": "unclear", "decision_confidence": "low", "likely_paper_type": "survey",
             "provider_ids": "openalex:WC1", "doi": "10.1/c", "year": "2022"},
        ]

    atomic_write_csv(decisions, [
        "candidate_id", "rank", "title", "decision", "decision_confidence", "likely_paper_type",
        "provider_ids", "doi", "year",
    ], decisions_rows)

    atomic_write_csv(artifact, [
        "artifact_id", "paper_id", "status", "artifact_type",
    ], [
        {"artifact_id": "A1", "paper_id": "doi:10.1/a", "status": "success", "artifact_type": "pdf"},
        {"artifact_id": "A2", "paper_id": "doi:10.1/a", "status": "success", "artifact_type": "jats_xml"},
        {"artifact_id": "A3", "paper_id": "doi:10.1/b", "status": "success", "artifact_type": "pdf"},
    ])

    ranking_dir = repo / "outputs/fulltext_ranking/runs/RANK_20260722T210245Z"
    ranking_dir.mkdir(parents=True, exist_ok=True)
    ranking_path = ranking_dir / "next_20_fulltext.csv"
    return repo, ranking_path


def _write_ranking_csv(ranking_path: Path, rows: list[dict[str, str]]) -> Path:
    atomic_write_csv(ranking_path, RANKING_FIELDS, rows)
    return ranking_path


def _make_ranking_row(candidate_id: str, screening_rank: str, rec_rank: str, title: str, year: str = "2024", **kw):
    row = {
        "candidate_id": candidate_id,
        "original_screening_rank": screening_rank,
        "recommended_fulltext_rank": rec_rank,
        "title": title,
        "year": year,
        "authors": "Author", "venue": "Venue", "doi": "",
        "arxiv_id": "", "pmid": "", "pmcid": "",
        "landing_url": "", "pdf_url": "", "is_open_access": "False",
        "provider_ids": "", "priority_score": "5", "likely_paper_type": "",
    }
    row.update(kw)
    return row


# --- Existing legacy test ---

def test_build_queue(tmp_path: Path):
    repo = make_repo(tmp_path)
    settings = load_settings(repo)
    works = load_eligible_works(settings)
    assert len(works) == 1
    assert works[0].pmcid == "PMC123"
    assert works[0].openalex_id == "W1"
    path = build_queue(settings, out_dir=repo / "outputs/fulltext/test_queue")
    _, rows = read_csv(path)
    assert rows[0]["paper_id"] == "doi:10.1/test"
    assert rows[0]["pdf_status"] == "missing"


# --- Happy path ---

def test_build_queue_from_ranking_basic(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A", "2024",
                          authors="Author A", venue="Venue A",
                          pmcid="PMC1", is_open_access="True",
                          provider_ids="openalex:WA1", priority_score="8",
                          likely_paper_type="dataset_paper"),
        _make_ranking_row("doi:10.1/b", "2", "2", "Paper B", "2023",
                          authors="Author B", venue="Venue B",
                          pmcid="PMC2", is_open_access="True",
                          provider_ids="openalex:WB1", priority_score="7",
                          likely_paper_type="method_paper"),
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_rank_queue")
    _, rows = read_csv(path)
    assert len(rows) == 2
    assert rows[0]["paper_id"] == "doi:10.1/a"
    assert rows[0]["rank"] == "1"
    assert rows[0]["screening_decision"] == "include"
    assert rows[0]["acquisition_status"] == "complete"
    assert rows[0]["pdf_status"] == "available"
    assert rows[0]["structured_status"] == "available"
    assert rows[0]["acquisition_batch_id"] != ""
    assert rows[0]["ranking_position"] == "1"
    assert rows[0]["ranking_run_id"] != ""
    assert rows[0]["ranking_source_sha256"] != ""
    assert rows[1]["paper_id"] == "doi:10.1/b"
    assert rows[1]["acquisition_status"] == "partial"
    assert rows[1]["pdf_status"] == "available"
    assert rows[1]["structured_status"] == "missing"
    assert rows[1]["ranking_position"] == "2"

    manifest = read_json(path.parent / "queue_manifest.json")
    assert manifest["validation_status"] == "passed"
    assert manifest["selected_count"] == 2
    assert manifest["selection_policy"] == "exact-top-n"

    batch_snapshot = repo / "data/curated/fulltext/acquisition_batches" / rows[0]["acquisition_batch_id"]
    assert batch_snapshot.exists()
    assert (batch_snapshot / "selection.csv").exists()
    assert (batch_snapshot / "manifest.json").exists()
    snap_manifest = read_json(batch_snapshot / "manifest.json")
    assert snap_manifest["ordered_candidate_ids"] == ["doi:10.1/a", "doi:10.1/b"]
    assert snap_manifest["validation_status"] == "passed"

    _, sel_rows = read_csv(batch_snapshot / "selection.csv")
    assert len(sel_rows) == 2
    assert sel_rows[0]["candidate_id"] == "doi:10.1/a"
    assert sel_rows[1]["candidate_id"] == "doi:10.1/b"

    batch_path = repo / "data/curated/fulltext/fulltext_acquisition_batches.csv"
    assert batch_path.exists()
    _, batch_rows = read_csv(batch_path)
    assert len(batch_rows) >= 1
    last = batch_rows[-1]
    assert last["validation_status"] == "passed"
    assert last["selected_count"] == "2"


# --- Limit tests ---

def test_build_queue_from_ranking_limit(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
        _make_ranking_row("doi:10.1/b", "2", "2", "Paper B"),
    ])
    path = build_queue_from_ranking(settings, ranking_path, limit=1, out_dir=repo / "outputs/fulltext/test_rank_limit")
    _, rows = read_csv(path)
    assert len(rows) == 1
    assert rows[0]["paper_id"] == "doi:10.1/a"


def test_build_queue_from_ranking_limit_exceeds_cap(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [_make_ranking_row("doi:10.1/a", "1", "1", "Paper A")])
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        build_queue_from_ranking(settings, ranking_path, limit=99)


def test_build_queue_from_ranking_limit_negative(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [_make_ranking_row("doi:10.1/a", "1", "1", "Paper A")])
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        build_queue_from_ranking(settings, ranking_path, limit=-1)


# --- skip-complete ---

def test_build_queue_from_ranking_skip_complete(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
        _make_ranking_row("doi:10.1/b", "2", "2", "Paper B", year="2023"),
    ])
    # With limit=1 and skip-complete: A is complete, so skip it, B fills the slot → 1 row
    path = build_queue_from_ranking(settings, ranking_path, skip_complete=True, limit=1, out_dir=repo / "outputs/fulltext/test_skip_1")
    _, rows = read_csv(path)
    assert len(rows) == 1
    assert rows[0]["paper_id"] == "doi:10.1/b"

    # With limit=2 and skip-complete, A is skipped, B is included → 1 row
    path = build_queue_from_ranking(settings, ranking_path, skip_complete=True, limit=2, out_dir=repo / "outputs/fulltext/test_skip_ok")
    _, rows = read_csv(path)
    assert len(rows) == 1
    assert rows[0]["paper_id"] == "doi:10.1/b"


# --- Strict fail on errors ---

def test_build_queue_from_ranking_duplicate_id_fails(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
        _make_ranking_row("doi:10.1/a", "1", "2", "Paper A dup"),
    ])
    with pytest.raises(QueueValidationError, match="Duplicate"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_dup")


def test_build_queue_from_ranking_not_in_decisions_fails(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/unknown", "99", "1", "Unknown"),
    ])
    with pytest.raises(QueueValidationError, match="not found in decisions"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_missing")


def test_build_queue_from_ranking_excluded_fails(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path, decisions_rows=[
        {"candidate_id": "doi:10.1/x", "rank": "99", "title": "Excluded Paper",
         "decision": "exclude", "decision_confidence": "high", "likely_paper_type": "",
         "provider_ids": "", "doi": "10.1/x", "year": "2024"},
    ])
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/x", "99", "1", "Excluded Paper"),
    ])
    with pytest.raises(QueueValidationError, match="not active"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_excluded")


def test_build_queue_from_ranking_identity_conflict_fails(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Completely Different Title", year="2025"),
    ])
    with pytest.raises(QueueValidationError, match="Identity conflict"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_conflict")


def test_build_queue_from_ranking_rank_mismatch_fails(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "99", "1", "Paper A"),  # rank 99 ≠ authoritative rank 1
    ])
    with pytest.raises(QueueValidationError, match="rank mismatch"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_rank_mismatch")


def test_build_queue_from_ranking_paper_id_mismatch_fails(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A", paper_id="doi:10.1/wrong"),
    ])
    with pytest.raises(QueueValidationError, match="does not match candidate_id"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_paperid_mismatch")


# --- allow-partial ---

def test_build_queue_from_ranking_allow_partial(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path, decisions_rows=[
        {"candidate_id": "doi:10.1/a", "rank": "1", "title": "Paper A",
         "decision": "include", "decision_confidence": "high", "likely_paper_type": "dataset_paper",
         "provider_ids": "openalex:WA1", "doi": "10.1/a", "year": "2024"},
        {"candidate_id": "doi:10.1/b", "rank": "2", "title": "Paper B",
         "decision": "include", "decision_confidence": "medium", "likely_paper_type": "method_paper",
         "provider_ids": "openalex:WB1", "doi": "10.1/b", "year": "2023"},
        {"candidate_id": "doi:10.1/c", "rank": "3", "title": "Paper C",
         "decision": "exclude", "decision_confidence": "high", "likely_paper_type": "",
         "provider_ids": "", "doi": "10.1/c", "year": "2022"},
    ])
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
        _make_ranking_row("doi:10.1/c", "3", "2", "Paper C"),  # excluded
    ])
    # Without --allow-partial, this fails
    with pytest.raises(QueueValidationError):
        build_queue_from_ranking(settings, ranking_path, selection_policy="first-n-eligible", out_dir=repo / "outputs/fulltext/test_partial_no")

    # With --allow-partial and first-n-eligible, we get only paper A
    path = build_queue_from_ranking(settings, ranking_path, selection_policy="first-n-eligible", allow_partial=True, out_dir=repo / "outputs/fulltext/test_partial_yes")
    _, rows = read_csv(path)
    assert len(rows) == 1
    assert rows[0]["paper_id"] == "doi:10.1/a"

    manifest = read_json(path.parent / "queue_manifest.json")
    assert manifest["validation_status"] == "partial"

    batch_snapshot = repo / "data/curated/fulltext/acquisition_batches" / rows[0]["acquisition_batch_id"]
    assert batch_snapshot.exists()
    snap_manifest = read_json(batch_snapshot / "manifest.json")
    assert snap_manifest["validation_status"] == "partial"

    _, batch_rows = read_csv(repo / "data/curated/fulltext/fulltext_acquisition_batches.csv")
    assert batch_rows[-1]["validation_status"] == "partial"


# --- Default limit cap ---

def test_build_queue_from_ranking_default_limit(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    rows = []
    for i in range(60):
        cid = f"doi:10.1/paper{i}"
        rows.append(_make_ranking_row(cid, str(i + 1), str(i + 1), f"Paper {i}"))
    _write_ranking_csv(ranking_path, rows)

    decisions = repo / "data/curated/screening/title_abstract_decisions_enriched.csv"
    _, existing = read_csv(decisions)
    extra_rows = [
        {"candidate_id": f"doi:10.1/paper{i}", "rank": str(i + 1), "title": f"Paper {i}",
         "decision": "include", "decision_confidence": "medium", "likely_paper_type": "",
         "provider_ids": "", "doi": f"doi:10.1/paper{i}", "year": "2024"}
        for i in range(60)
    ]
    append_csv(decisions, list(existing[0].keys()), extra_rows)

    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_default_limit")
    _, result = read_csv(path)
    assert len(result) == 50  # capped at 50


# --- Selection policy: first-n-eligible ---

def test_build_queue_from_ranking_first_n_eligible(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path, decisions_rows=[
        {"candidate_id": "doi:10.1/a", "rank": "1", "title": "Paper A",
         "decision": "include", "decision_confidence": "high", "likely_paper_type": "dataset_paper",
         "provider_ids": "openalex:WA1", "doi": "10.1/a", "year": "2024"},
        {"candidate_id": "doi:10.1/b", "rank": "2", "title": "Paper B",
         "decision": "include", "decision_confidence": "medium", "likely_paper_type": "method_paper",
         "provider_ids": "openalex:WB1", "doi": "10.1/b", "year": "2023"},
    ])
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A", year="2024"),
        _make_ranking_row("doi:10.1/unknown", "99", "2", "Unknown"),
        _make_ranking_row("doi:10.1/b", "2", "3", "Paper B", year="2023"),
    ])
    # first-n-eligible skips the unknown, includes A and B
    path = build_queue_from_ranking(settings, ranking_path, selection_policy="first-n-eligible", limit=2, allow_partial=True, out_dir=repo / "outputs/fulltext/test_fne")
    _, rows = read_csv(path)
    assert len(rows) == 2
    assert rows[0]["paper_id"] == "doi:10.1/a"
    assert rows[1]["paper_id"] == "doi:10.1/b"


# --- Stable ID identity handling ---

def test_build_queue_from_ranking_stable_id_warning(tmp_path: Path):
    """Same DOI but different title → warning not error."""
    repo, ranking_path = make_ranking_repo(tmp_path, decisions_rows=[
        {"candidate_id": "doi:10.1/a", "rank": "1", "title": "Original Title",
         "decision": "include", "decision_confidence": "high", "likely_paper_type": "dataset_paper",
         "provider_ids": "openalex:WA1", "doi": "10.1/a", "year": "2024"},
    ])
    settings = load_settings(repo)
    ranking_row = _make_ranking_row("doi:10.1/a", "1", "1", "Different Title")
    ranking_row["doi"] = "10.1/a"  # same DOI
    _write_ranking_csv(ranking_path, [ranking_row])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_stable")
    _, rows = read_csv(path)
    assert len(rows) == 1  # succeeds because DOI matches


def test_build_queue_from_ranking_no_stable_id_title_mismatch_fails(tmp_path: Path):
    """No DOI/arXiv/PMID but title differs → error."""
    repo, ranking_path = make_ranking_repo(tmp_path, decisions_rows=[
        {"candidate_id": "doi:10.1/a", "rank": "1", "title": "Original Title",
         "decision": "include", "decision_confidence": "high", "likely_paper_type": "dataset_paper",
         "provider_ids": "", "doi": "", "year": "2024"},
    ])
    settings = load_settings(repo)
    ranking_row = _make_ranking_row("doi:10.1/a", "1", "1", "Different Title")
    ranking_row["doi"] = ""  # no DOI
    _write_ranking_csv(ranking_path, [ranking_row])
    with pytest.raises(QueueValidationError, match="Identity conflict"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_no_id")


# --- Repo-relative paths ---

def test_build_queue_from_ranking_repo_relative_paths(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_rel")
    manifest = read_json(path.parent / "queue_manifest.json")
    assert "C:" not in manifest["queue_path"]
    assert manifest["queue_path"].startswith("outputs/")
    assert "C:" not in manifest["ranking_source"]
    assert manifest["ranking_source"].startswith("outputs/fulltext_ranking")

    batch_id = read_csv(path)[1][0]["acquisition_batch_id"]
    snap_manifest = read_json(repo / "data/curated/fulltext/acquisition_batches" / batch_id / "manifest.json")
    assert "C:" not in snap_manifest["queue_path"]
    assert "C:" not in snap_manifest["ranking_source"]


# --- Exit code on validation failure ---

def test_build_queue_from_ranking_exit_code(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/unknown", "99", "1", "Unknown"),
    ])
    from agri_fulltext.queueing import build_queue_from_ranking
    import subprocess
    with pytest.raises(QueueValidationError, match="not found in decisions"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_exit")


# --- CLI mutual exclusivity ---

def test_cli_ranking_options_rejected_in_rank_mode(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    _write_ranking_csv(ranking_path, [_make_ranking_row("doi:10.1/a", "1", "1", "Paper A")])
    from agri_fulltext.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["--repo", str(repo), "queue", "--ranks", "1-10", "--limit", "5"])
    assert exc.value.code != 0


# --- Queue has provenance columns ---

def test_build_queue_from_ranking_has_provenance_columns(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_prov")
    _, rows = read_csv(path)
    assert "acquisition_batch_id" in rows[0]
    assert "ranking_position" in rows[0]
    assert "ranking_run_id" in rows[0]
    assert "ranking_source_sha256" in rows[0]


# --- Empty CSV ---

def test_build_queue_from_ranking_empty_csv(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [])
    with pytest.raises(SystemExit, match="No rows found"):
        build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_empty")


# --- Ranking run ID extraction ---

def test_ranking_run_id_extracted(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    # Create ranking CSV with RANK_ in path
    rank_dir = repo / "outputs/fulltext_ranking/runs/RANK_20260722T210245Z"
    rank_dir.mkdir(parents=True, exist_ok=True)
    ranking_path2 = rank_dir / "next_20_fulltext.csv"
    _write_ranking_csv(ranking_path2, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),
    ])
    path = build_queue_from_ranking(settings, ranking_path2, out_dir=repo / "outputs/fulltext/test_runid")
    _, rows = read_csv(path)
    assert rows[0]["ranking_run_id"] == "RANK_20260722T210245Z"


# --- Authoritative rank is used, not ranking-provided rank ---

def test_authoritative_rank_used(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        _make_ranking_row("doi:10.1/a", "1", "1", "Paper A"),  # ranking says rank=1
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_auth_rank")
    _, rows = read_csv(path)
    assert rows[0]["rank"] == "1"  # authoritative rank from decisions
