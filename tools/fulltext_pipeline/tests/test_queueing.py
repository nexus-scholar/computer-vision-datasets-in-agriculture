import json
from pathlib import Path

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import atomic_write_csv, read_csv, read_json
from agri_fulltext.queueing import build_queue, build_queue_from_ranking, load_eligible_works


RANKING_FIELDS = [
    "candidate_id", "original_screening_rank", "recommended_fulltext_rank",
    "title", "year", "authors", "venue", "doi", "arxiv_id", "pmid", "pmcid",
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

    ranking_path = repo / "ranking_input.csv"
    return repo, ranking_path


def _write_ranking_csv(ranking_path: Path, rows: list[dict[str, str]]) -> Path:
    atomic_write_csv(ranking_path, RANKING_FIELDS, rows)
    return ranking_path


# --- Existing test ---

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


# --- build_queue_from_ranking tests ---

def test_build_queue_from_ranking_basic(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Paper A", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
        {"candidate_id": "doi:10.1/b", "original_screening_rank": "2", "recommended_fulltext_rank": "2",
         "title": "Paper B", "year": "2023", "authors": "Author B", "venue": "Venue B", "doi": "10.1/b",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC2", "landing_url": "https://b.org",
         "pdf_url": "https://b.org/b.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WB1", "priority_score": "7", "likely_paper_type": "method_paper"},
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
    assert rows[1]["paper_id"] == "doi:10.1/b"
    assert rows[1]["acquisition_status"] == "partial"
    assert rows[1]["pdf_status"] == "available"
    assert rows[1]["structured_status"] == "missing"

    manifest = read_json(path.parent / "queue_manifest.json")
    assert manifest["eligible_works"] == 2
    assert manifest["validation_errors"] == 0

    batch_path = repo / "data/curated/fulltext/fulltext_acquisition_batches.csv"
    assert batch_path.exists()
    _, batch_rows = read_csv(batch_path)
    assert len(batch_rows) == 1
    assert batch_rows[0]["paper_count"] == "2"


def test_build_queue_from_ranking_limit(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Paper A", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
        {"candidate_id": "doi:10.1/b", "original_screening_rank": "2", "recommended_fulltext_rank": "2",
         "title": "Paper B", "year": "2023", "authors": "Author B", "venue": "Venue B", "doi": "10.1/b",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC2", "landing_url": "https://b.org",
         "pdf_url": "https://b.org/b.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WB1", "priority_score": "7", "likely_paper_type": "method_paper"},
    ])
    path = build_queue_from_ranking(settings, ranking_path, limit=1, out_dir=repo / "outputs/fulltext/test_rank_limit")
    _, rows = read_csv(path)
    assert len(rows) == 1
    assert rows[0]["paper_id"] == "doi:10.1/a"


def test_build_queue_from_ranking_skip_complete(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Paper A", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
        {"candidate_id": "doi:10.1/b", "original_screening_rank": "2", "recommended_fulltext_rank": "2",
         "title": "Paper B", "year": "2023", "authors": "Author B", "venue": "Venue B", "doi": "10.1/b",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC2", "landing_url": "https://b.org",
         "pdf_url": "https://b.org/b.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WB1", "priority_score": "7", "likely_paper_type": "method_paper"},
        {"candidate_id": "doi:10.1/c", "original_screening_rank": "3", "recommended_fulltext_rank": "3",
         "title": "Paper C", "year": "2022", "authors": "Author C", "venue": "Venue C", "doi": "10.1/c",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC3", "landing_url": "https://c.org",
         "pdf_url": "", "is_open_access": "False",
         "provider_ids": "openalex:WC1", "priority_score": "6", "likely_paper_type": "survey"},
    ])
    path = build_queue_from_ranking(settings, ranking_path, skip_complete=True, out_dir=repo / "outputs/fulltext/test_skip")
    _, rows = read_csv(path)
    assert len(rows) == 2
    assert rows[0]["paper_id"] == "doi:10.1/b"
    assert rows[1]["paper_id"] == "doi:10.1/c"


def test_build_queue_from_ranking_duplicate_id(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Paper A", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "2",
         "title": "Paper A duplicate", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_dup")
    _, rows = read_csv(path)
    assert len(rows) == 1
    assert rows[0]["paper_id"] == "doi:10.1/a"

    errors = read_json(path.parent / "ranking_validation_errors.json")
    assert any("Duplicate" in e and "doi:10.1/a" in e for e in errors)


def test_build_queue_from_ranking_not_in_decisions(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/unknown", "original_screening_rank": "99", "recommended_fulltext_rank": "1",
         "title": "Unknown Paper", "year": "2024", "authors": "Author X", "venue": "Venue X", "doi": "10.1/unknown",
         "arxiv_id": "", "pmid": "", "pmcid": "", "landing_url": "", "pdf_url": "",
         "is_open_access": "False", "provider_ids": "", "priority_score": "5", "likely_paper_type": ""},
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_missing")
    _, rows = read_csv(path)
    assert len(rows) == 0

    errors = read_json(path.parent / "ranking_validation_errors.json")
    assert any("not found in decisions" in e for e in errors)


def test_build_queue_from_ranking_excluded(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path, decisions_rows=[
        {"candidate_id": "doi:10.1/x", "rank": "99", "title": "Excluded Paper",
         "decision": "exclude", "decision_confidence": "high", "likely_paper_type": "",
         "provider_ids": "", "doi": "10.1/x", "year": "2024"},
    ])
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/x", "original_screening_rank": "99", "recommended_fulltext_rank": "1",
         "title": "Excluded Paper", "year": "2024", "authors": "Author X", "venue": "Venue X", "doi": "10.1/x",
         "arxiv_id": "", "pmid": "", "pmcid": "", "landing_url": "", "pdf_url": "",
         "is_open_access": "False", "provider_ids": "", "priority_score": "5", "likely_paper_type": ""},
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_excluded")
    _, rows = read_csv(path)
    assert len(rows) == 0

    errors = read_json(path.parent / "ranking_validation_errors.json")
    assert any("not active" in e and "exclude" in e for e in errors)


def test_build_queue_from_ranking_identity_conflict(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Completely Different Title", "year": "2025", "authors": "Author A", "venue": "Venue A",
         "doi": "10.1/a", "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_conflict")
    _, rows = read_csv(path)
    assert len(rows) == 0

    errors = read_json(path.parent / "ranking_validation_errors.json")
    assert any("Identity conflict" in e for e in errors)


def test_build_queue_from_ranking_multimix(tmp_path: Path):
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
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Paper A", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
        {"candidate_id": "doi:10.1/b", "original_screening_rank": "2", "recommended_fulltext_rank": "2",
         "title": "Paper B", "year": "2023", "authors": "Author B", "venue": "Venue B", "doi": "10.1/b",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC2", "landing_url": "https://b.org",
         "pdf_url": "https://b.org/b.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WB1", "priority_score": "7", "likely_paper_type": "method_paper"},
        {"candidate_id": "doi:10.1/c", "original_screening_rank": "3", "recommended_fulltext_rank": "3",
         "title": "Paper C", "year": "2022", "authors": "Author C", "venue": "Venue C", "doi": "10.1/c",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC3", "landing_url": "https://c.org",
         "pdf_url": "", "is_open_access": "False",
         "provider_ids": "openalex:WC1", "priority_score": "6", "likely_paper_type": "survey"},
        {"candidate_id": "doi:10.1/a", "original_screening_rank": "1", "recommended_fulltext_rank": "4",
         "title": "Paper A duplicate", "year": "2024", "authors": "Author A", "venue": "Venue A", "doi": "10.1/a",
         "arxiv_id": "", "pmid": "", "pmcid": "PMC1", "landing_url": "https://a.org",
         "pdf_url": "https://a.org/a.pdf", "is_open_access": "True",
         "provider_ids": "openalex:WA1", "priority_score": "8", "likely_paper_type": "dataset_paper"},
    ])
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_mix")
    _, rows = read_csv(path)
    assert len(rows) == 2
    assert rows[0]["paper_id"] == "doi:10.1/a"
    assert rows[1]["paper_id"] == "doi:10.1/b"

    errors = read_json(path.parent / "ranking_validation_errors.json")
    assert len(errors) == 2
    assert any("not active" in e for e in errors)
    assert any("Duplicate" in e for e in errors)


def test_build_queue_from_ranking_default_limit(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    rows = []
    for i in range(60):
        cid = f"doi:10.1/paper{i}"
        rows.append({
            "candidate_id": cid, "original_screening_rank": str(i + 1), "recommended_fulltext_rank": str(i + 1),
            "title": f"Paper {i}", "year": "2024", "authors": "Author", "venue": "Venue", "doi": cid,
            "arxiv_id": "", "pmid": "", "pmcid": "", "landing_url": "", "pdf_url": "",
            "is_open_access": "False", "provider_ids": "", "priority_score": "5", "likely_paper_type": "",
        })
    _write_ranking_csv(ranking_path, rows)

    from agri_fulltext.io_utils import append_csv
    from agri_fulltext.schema import FULLTEXT_QUEUE_FIELDS
    decisions = repo / "data/curated/screening/title_abstract_decisions_enriched.csv"
    _, existing = read_csv(decisions)
    extra_rows = [
        {"candidate_id": f"doi:10.1/paper{i}", "rank": str(i + 1), "title": f"Paper {i}",
         "decision": "include", "decision_confidence": "medium", "likely_paper_type": "",
         "provider_ids": "", "doi": f"doi:10.1/paper{i}", "year": "2024"}
        for i in range(3, 60)
    ]
    append_csv(decisions, list(existing[0].keys()), extra_rows)

    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo / "outputs/fulltext/test_default_limit")
    _, result = read_csv(path)
    assert len(result) <= 50


def test_build_queue_from_ranking_id_detection_priority(tmp_path: Path):
    repo_path = tmp_path / "repo"
    (repo_path / "config").mkdir(parents=True)
    queue_path = repo_path / "outputs/screening_queue_2026-07-22/screening_queue.csv"
    decisions_path = repo_path / "data/curated/screening/title_abstract_decisions_enriched.csv"
    atomic_write_csv(queue_path, [
        "screening_rank", "canonical_paper_id", "title",
    ], [{"screening_rank": "1", "canonical_paper_id": "canon:1", "title": "Test"}])
    atomic_write_csv(decisions_path, [
        "candidate_id", "rank", "title", "decision", "decision_confidence", "likely_paper_type",
        "provider_ids", "doi", "year",
    ], [{"candidate_id": "doi:10.1/real", "rank": "1", "title": "Test", "decision": "include",
         "decision_confidence": "high", "likely_paper_type": "", "provider_ids": "", "doi": "10.1/real", "year": "2024"}])
    atomic_write_csv(repo_path / "data/curated/fulltext/artifact_registry.csv", [
        "artifact_id", "paper_id", "status", "artifact_type",
    ], [])

    ranking_path = repo_path / "ranking.csv"
    _write_ranking_csv(ranking_path, [
        {"candidate_id": "doi:10.1/real", "original_screening_rank": "1", "recommended_fulltext_rank": "1",
         "title": "Test", "year": "2024", "authors": "", "venue": "", "doi": "10.1/real",
         "arxiv_id": "", "pmid": "", "pmcid": "", "landing_url": "", "pdf_url": "",
         "is_open_access": "False", "provider_ids": "", "priority_score": "5", "likely_paper_type": ""},
    ])
    settings = load_settings(repo_path)
    path = build_queue_from_ranking(settings, ranking_path, out_dir=repo_path / "outputs/fulltext/test_id")
    _, rows = read_csv(path)
    assert rows[0]["screening_decision"] == "include"


def test_build_queue_from_ranking_empty_csv(tmp_path: Path):
    repo, ranking_path = make_ranking_repo(tmp_path)
    settings = load_settings(repo)
    _write_ranking_csv(ranking_path, [])

    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-c", f"""
import sys; sys.path.insert(0, r'{repo.parent.parent / "tools/fulltext_pipeline/src"}')
from pathlib import Path; from agri_fulltext.config import load_settings
from agri_fulltext.queueing import build_queue_from_ranking
try:
    build_queue_from_ranking(load_settings(Path(r'{repo}')), Path(r'{ranking_path}'))
    print("NO_ERROR")
except SystemExit as e:
    print(f"ERROR:{{e}}")
except Exception as e:
    print(f"EXC:{{e}}")
"""],
        capture_output=True, text=True, timeout=30,
    )
    assert "ERROR" in result.stdout or "EXC" in result.stdout
