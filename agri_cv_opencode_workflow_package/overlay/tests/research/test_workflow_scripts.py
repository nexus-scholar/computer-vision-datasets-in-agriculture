from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[2]
AUDIT = load_module("audit_snowball_run", ROOT / "scripts" / "research" / "audit_snowball_run.py")
QUEUE = load_module("prepare_screening_queue", ROOT / "scripts" / "research" / "prepare_screening_queue.py")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_audit_quarantines_accepted_low_confidence_seed(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    write_csv(run / "seed_papers_provider_metadata.csv", [
        "seed_row_id", "provider", "match_status", "match_method", "match_score", "source_input_title", "title"
    ], [{
        "seed_row_id": "P004", "provider": "openalex", "match_status": "low_confidence",
        "match_method": "low_confidence_search_title", "match_score": "0.38",
        "source_input_title": "A Dataset for Semantic and Instance Segmentation of Modern Fruit Orchards",
        "title": "Intelligent Fruit Yield Estimation for Orchards A Review",
    }])
    write_csv(run / "run_summary.csv", [
        "seed_row_id", "provider", "status", "reported_reference_count", "downloaded_reference_rows",
        "reported_citation_count", "downloaded_citation_rows"
    ], [{
        "seed_row_id": "P004", "provider": "openalex", "status": "resolved",
        "reported_reference_count": 113, "downloaded_reference_rows": 113,
        "reported_citation_count": 128, "downloaded_citation_rows": 128,
    }])
    write_csv(run / "unresolved_seeds.csv", ["seed_row_id", "provider", "reason", "score", "cache_path"], [])
    edge_fields = [
        "seed_row_id", "dataset_name", "direction", "provider", "related_provider_work_id", "related_title",
        "related_year", "related_doi", "related_arxiv_id", "related_pmid", "related_pmcid"
    ]
    write_csv(run / "snowball_edges.csv", edge_fields, [{
        "seed_row_id": "P004", "dataset_name": "MFO", "direction": "forward_citation", "provider": "openalex",
        "related_provider_work_id": "W1", "related_title": "Example", "related_year": "2025", "related_doi": "10.1/x",
    }])
    write_csv(run / "snowball_nodes.csv", ["node_key", "title", "year"], [{"node_key": "doi:10.1/x", "title": "Example", "year": "2025"}])
    (run / "run_manifest.json").write_text(json.dumps({
        "seed_count": 1, "max_backward_references": 0, "max_forward_citations": 0,
        "openalex_mailto_used": False, "semantic_scholar_api_key_used": False,
    }), encoding="utf-8")

    issues, metrics, quarantine = AUDIT.audit(run, 0.88)
    assert "P004" in quarantine
    assert not metrics["quality_gate_passed"]
    assert any(issue.code == "accepted_low_confidence_seed" for issue in issues)


def test_queue_canonicalizes_cross_provider_doi(tmp_path: Path, monkeypatch) -> None:
    edges = tmp_path / "snowball_edges.csv"
    fields = [
        "seed_row_id", "dataset_name", "direction", "provider", "related_provider_work_id", "related_title",
        "related_year", "related_publication_date", "related_authors", "related_venue", "related_journal",
        "related_doi", "related_arxiv_id", "related_pmid", "related_pmcid", "related_url", "related_pdf_url",
        "related_is_open_access", "related_citation_count", "related_reference_count", "abstract"
    ]
    rows = []
    for provider, work_id in (("openalex", "W1"), ("semantic_scholar", "S1")):
        rows.append({
            "seed_row_id": "P010", "dataset_name": "WeedsGalore", "direction": "forward_citation",
            "provider": provider, "related_provider_work_id": work_id, "related_title": "Robust crop segmentation dataset",
            "related_year": "2025", "related_doi": "10.1000/example", "related_citation_count": "3",
            "abstract": "A multispectral agricultural segmentation benchmark.",
        })
    write_csv(edges, fields, rows)
    out = tmp_path / "queue.csv"
    monkeypatch.setattr("sys.argv", ["prepare_screening_queue.py", str(edges), "--out", str(out)])
    assert QUEUE.main() == 0
    with out.open("r", encoding="utf-8", newline="") as handle:
        queue = list(csv.DictReader(handle))
    assert len(queue) == 1
    assert queue[0]["providers"] == "openalex; semantic_scholar"
    assert queue[0]["provider_edge_rows"] == "2"

GRAPH = load_module("build_accepted_graph", ROOT / "scripts" / "research" / "build_accepted_graph.py")


def make_graph_run(path: Path, *, provider_work_id: str, edge_title: str, downloaded: int = 1, reported: int = 1) -> None:
    path.mkdir(parents=True)
    write_csv(path / "seed_papers_provider_metadata.csv", [
        "seed_row_id", "dataset_name", "provider", "provider_work_id", "doi", "title", "match_status"
    ], [{
        "seed_row_id": "P001", "dataset_name": "Dataset", "provider": "openalex",
        "provider_work_id": provider_work_id, "doi": "10.1000/correct", "title": "Correct seed", "match_status": "live",
    }])
    write_csv(path / "run_summary.csv", [
        "seed_row_id", "provider", "reported_reference_count", "downloaded_reference_rows",
        "reported_citation_count", "downloaded_citation_rows"
    ], [{
        "seed_row_id": "P001", "provider": "openalex", "reported_reference_count": reported,
        "downloaded_reference_rows": downloaded, "reported_citation_count": 0, "downloaded_citation_rows": 0,
    }])
    write_csv(path / "snowball_edges.csv", [
        "seed_row_id", "dataset_name", "provider", "direction", "seed_provider_work_id",
        "related_provider_work_id", "related_title", "related_year", "related_doi"
    ], [{
        "seed_row_id": "P001", "dataset_name": "Dataset", "provider": "openalex",
        "direction": "backward_reference", "seed_provider_work_id": provider_work_id,
        "related_provider_work_id": "WREL", "related_title": edge_title, "related_year": "2025",
        "related_doi": "10.1000/related",
    }])
    (path / "run_manifest.json").write_text(json.dumps({
        "max_backward_references": 0, "max_forward_citations": 0,
    }), encoding="utf-8")


def write_seed_audit(path: Path) -> None:
    write_csv(path, [
        "seed_row_id", "dataset_name", "provider", "candidate_id", "candidate_doi", "identity_status"
    ], [{
        "seed_row_id": "P001", "dataset_name": "Dataset", "provider": "openalex",
        "candidate_id": "WNEW", "candidate_doi": "10.1000/correct", "identity_status": "accepted",
    }])


def test_accepted_graph_selects_newest_exact_identity(tmp_path: Path, monkeypatch) -> None:
    old = tmp_path / "old"
    new = tmp_path / "new"
    make_graph_run(old, provider_work_id="WOLD", edge_title="Old wrong edge")
    make_graph_run(new, provider_work_id="WNEW", edge_title="New accepted edge")
    audit = tmp_path / "seed_resolution_audit.csv"
    write_seed_audit(audit)
    out = tmp_path / "accepted"
    monkeypatch.setattr("sys.argv", [
        "build_accepted_graph.py", "--runs", str(old), str(new), "--seed-audit", str(audit), "--out", str(out)
    ])
    assert GRAPH.main() == 0
    with (out / "accepted_snowball_edges.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["related_title"] == "New accepted edge"
    assert rows[0]["source_run"] == str(new.resolve())


def test_accepted_graph_omits_incomplete_relations(tmp_path: Path, monkeypatch) -> None:
    run = tmp_path / "run"
    make_graph_run(run, provider_work_id="WNEW", edge_title="Incomplete edge", downloaded=0, reported=1)
    audit = tmp_path / "seed_resolution_audit.csv"
    write_seed_audit(audit)
    out = tmp_path / "accepted"
    monkeypatch.setattr("sys.argv", [
        "build_accepted_graph.py", "--runs", str(run), "--seed-audit", str(audit), "--out", str(out)
    ])
    assert GRAPH.main() == 2
    with (out / "accepted_snowball_edges.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == []
    issues = list(csv.DictReader((out / "build_issues.csv").open(encoding="utf-8", newline="")))
    assert any(row["code"] == "relation_count_shortfall" for row in issues)
