from pathlib import Path

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import atomic_write_csv, read_csv
from agri_fulltext.queueing import build_queue, load_eligible_works


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
