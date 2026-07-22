from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_repo(tmp_path: Path, n: int = 12) -> Path:
    repo = tmp_path
    (repo / "config").mkdir()
    source_config = Path(__file__).parents[2] / "config/fulltext_ranking.toml"
    (repo / "config/fulltext_ranking.toml").write_text(source_config.read_text(encoding="utf-8"), encoding="utf-8")
    decisions: list[dict[str, str]] = []
    queue: list[dict[str, str]] = []
    for i in range(1, n + 1):
        cid = f"doi:10.0000/test{i}"
        direct = i % 3 == 0
        relation = "uses_dataset_experimentally" if direct else "introduces_dataset"
        decisions.append({
            "screening_id": f"TA{i}", "candidate_id": cid, "rank": str(i), "title": f"Paper {i}",
            "decision": "include", "decision_confidence": "medium" if i % 5 == 0 else "high",
            "reason_code": "I02" if direct else "I01", "reason_note": "dataset evidence",
            "likely_paper_type": "method_paper" if direct else "dataset_paper",
            "likely_dataset_relationship": relation, "named_datasets": f"D{i % 4}",
            "agricultural_domain": "weeds", "vision_task": "semantic_segmentation",
            "modalities": "RGB;multispectral" if direct else "RGB",
            "relevance_yes": "semantic_segmentation;multispectral;cross_sensor" if direct else "semantic_segmentation",
            "relevance_unclear": "", "abstract_available": "yes", "full_text_available": "unknown",
            "identity_status": "confirmed", "reviewer": "ai", "model": "m",
            "protocol_version": "AI_SCREENING_V1", "screened_at": "2026-01-01T00:00:00Z",
            "batch_id": "B", "source_queue_sha256": "x", "supersedes_screening_id": "", "notes": "",
        })
        queue.append({
            "screening_rank": str(i), "canonical_paper_id": cid, "priority_score": str(20 - i),
            "priority_components": "", "title": f"Paper {i}", "year": str(2023 + i % 3),
            "publication_date": "", "authors": "A", "venue": "V", "journal": "J",
            "doi": cid.removeprefix("doi:"), "arxiv_id": "", "pmid": "", "pmcid": "",
            "landing_url": "", "pdf_url": "https://example.org/p.pdf" if i % 2 else "",
            "is_open_access": "True" if i % 2 else "False", "max_provider_citation_count": str(i * 2),
            "max_provider_reference_count": "10", "providers": "openalex",
            "provider_ids": f"openalex:W{i}", "seed_ids": f"P00{1 + i % 3}",
            "dataset_names": f"D{i % 4}", "directions": "forward_citation", "provider_edge_rows": "1",
            "abstract": ("Detailed agricultural segmentation dataset with 100 images and benchmark results. " * 20),
            "title_abstract_decision": "", "full_text_decision": "", "paper_role": "",
            "actual_dataset_use": "", "dataset_use_evidence": "", "exclusion_reason": "",
            "reviewer": "", "reviewed_date": "", "notes": "",
        })
    write_csv(repo / "data/curated/screening/title_abstract_decisions.csv", decisions)
    write_csv(repo / "outputs/screening_queue_test/screening_queue.csv", queue)
    (repo / "data/curated/ranking").mkdir(parents=True)
    (repo / "outputs/fulltext_ranking").mkdir(parents=True)
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).parents[2] / "scripts/research/fulltext_ranking.py"
    return subprocess.run([sys.executable, str(script), "--repo", str(repo), *args], text=True, capture_output=True)


def latest_run(repo: Path, pointer_name: str) -> Path:
    pointer = json.loads((repo / "outputs/fulltext_ranking" / pointer_name).read_text(encoding="utf-8"))
    return repo / pointer["run_dir"]


def test_bootstrap_ranks_all_included_with_sensitivity(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    result = run(repo, "bootstrap")
    assert result.returncode == 0, result.stderr
    run_dir = latest_run(repo, "latest_bootstrap.json")
    rows = list(csv.DictReader((run_dir / "recommended_fulltext_queue.csv").open(encoding="utf-8")))
    assert len(rows) == 12
    assert {row["recommended_fulltext_rank"] for row in rows} == {str(i) for i in range(1, 13)}
    assert {row["semantic_score_source"] for row in rows} == {"bootstrap"}
    assert all(row["rank_stability"] in {"stable", "moderate", "unstable"} for row in rows)
    assert all(row["pareto_layer"] for row in rows)
    assert (run_dir / "next_20_fulltext.csv").exists()


def test_prepare_uses_priority_queue_and_finalize_partial_ai_scores(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert run(repo, "bootstrap").returncode == 0
    prepared = run(repo, "prepare", "--range", "1-3")
    assert prepared.returncode == 0, prepared.stderr
    batch = repo / json.loads(prepared.stdout)["batch_dir"]
    with (batch / "scored_rows_template.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    for index, row in enumerate(rows, start=1):
        for field in (
            "project_fit", "dataset_evidence_value", "method_gap_value", "decision_leverage",
            "actual_use_likelihood", "evidence_specificity", "information_uncertainty",
        ):
            row[field] = str(min(4, index + 1))
        row.update({
            "estimated_reading_cost": str(index), "primary_role": "dataset_introduction",
            "primary_theme": "dataset_quality_and_benchmarking", "dataset_cluster": f"D{index}",
            "task_cluster": "semantic_segmentation", "modality_cluster": "RGB",
            "score_confidence": "high", "evidence_note": "Concrete dataset and segmentation evidence.",
            "reviewer": "opencode_ai", "model": "test-model",
            "scored_at": f"2026-01-0{index}T00:00:00Z",
        })
    write_csv(batch / "scored_rows.csv", rows)
    finalized = run(repo, "finalize-batch", "--batch", str(batch))
    assert finalized.returncode == 0, finalized.stderr
    built = run(repo, "build")
    assert built.returncode == 0, built.stderr
    run_dir = latest_run(repo, "latest_ranking.json")
    ranked = list(csv.DictReader((run_dir / "recommended_fulltext_queue.csv").open(encoding="utf-8")))
    assert len(ranked) == 12
    assert sum(row["semantic_score_source"] == "ai" for row in ranked) == 3
    assert sum(row["semantic_score_source"] == "bootstrap" for row in ranked) == 9


def test_identity_change_is_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert run(repo, "bootstrap").returncode == 0
    prepared = run(repo, "prepare", "--range", "1")
    batch = repo / json.loads(prepared.stdout)["batch_dir"]
    rows = list(csv.DictReader((batch / "scored_rows_template.csv").open(encoding="utf-8")))
    row = rows[0]
    row["title"] = "Changed title"
    for field in (
        "project_fit", "dataset_evidence_value", "method_gap_value", "decision_leverage",
        "actual_use_likelihood", "evidence_specificity", "information_uncertainty",
    ):
        row[field] = "3"
    row.update({
        "estimated_reading_cost": "2", "primary_role": "dataset_introduction",
        "primary_theme": "dataset_quality_and_benchmarking", "dataset_cluster": "D1",
        "task_cluster": "semantic_segmentation", "modality_cluster": "RGB",
        "score_confidence": "high", "evidence_note": "Evidence", "reviewer": "ai",
        "model": "m", "scored_at": "2026-01-01T00:00:00Z",
    })
    write_csv(batch / "scored_rows.csv", [row])
    result = run(repo, "finalize-batch", "--batch", str(batch))
    assert result.returncode == 1
    assert "validation failed" in result.stderr.lower()


def test_evaluation_compares_original_and_recommended(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert run(repo, "build").returncode == 0
    queue = list(csv.DictReader((latest_run(repo, "latest_ranking.json") / "recommended_fulltext_queue.csv").open(encoding="utf-8")))
    outcomes = []
    for index, row in enumerate(queue[:6], start=1):
        outcomes.append({
            "fulltext_screening_id": f"FT{index}", "paper_id": row["candidate_id"],
            "decision": "include_core" if index in {1, 3} else "include_supporting",
            "reviewed_at": f"2026-02-0{index}T00:00:00Z",
        })
    write_csv(repo / "data/curated/screening/full_text_decisions.csv", outcomes)
    evaluated = run(repo, "evaluate")
    assert evaluated.returncode == 0, evaluated.stderr
    data = json.loads(evaluated.stdout)
    assert "recommended" in data["orderings"]
    assert "original_screening" in data["orderings"]
    assert data["orderings"]["recommended"]["papers_to_first_core"] is not None
