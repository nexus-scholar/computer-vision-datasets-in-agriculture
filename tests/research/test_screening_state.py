from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from agri_cv_novelty.screening import CORE_FIELDS, validate_history

ROOT = Path(__file__).resolve().parents[2]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def base_row(screening_id: str, candidate: str, rank: int, decision: str = "include") -> dict[str, str]:
    row = {field: "" for field in CORE_FIELDS}
    row.update({
        "screening_id": screening_id,
        "candidate_id": candidate,
        "rank": str(rank),
        "title": f"Paper {rank}",
        "decision": decision,
        "decision_confidence": "high",
        "reason_code": "I05" if decision == "include" else "E03_NO_DATASET_RELEVANCE",
        "reason_note": "evidence-bound decision",
        "likely_paper_type": "method_paper",
        "likely_dataset_relationship": "no_dataset_relationship",
        "named_datasets": "",
        "agricultural_domain": "crop",
        "vision_task": "segmentation",
        "modalities": "RGB",
        "relevance_yes": "semantic_segmentation",
        "relevance_unclear": "",
        "abstract_available": "yes",
        "full_text_available": "unknown",
        "identity_status": "confirmed",
        "reviewer": "opencode_ai",
        "model": "test-model",
        "protocol_version": "AI_SCREENING_V1",
        "screened_at": "2026-07-22T00:00:00Z",
        "batch_id": "B001",
        "source_queue_sha256": "0" * 64,
        "supersedes_screening_id": "",
        "notes": "",
    })
    return row


def test_history_requires_explicit_supersession() -> None:
    first = base_row("TA_R0001", "doi:1", 1)
    correction = base_row("TA_R0001_QA1", "doi:1", 1, decision="exclude")
    errors, _ = validate_history([first, correction])
    assert any("lacks supersedes_screening_id" in error for error in errors)
    correction["supersedes_screening_id"] = "TA_R0001"
    errors, active = validate_history([first, correction])
    assert errors == []
    assert active[0]["decision"] == "exclude"


def test_prepare_and_finalize_batch(tmp_path: Path) -> None:
    repo = tmp_path
    queue_fields = [
        "screening_rank", "canonical_paper_id", "title", "year", "authors", "venue", "doi", "arxiv_id",
        "pmid", "pmcid", "providers", "provider_ids", "seed_ids", "dataset_names", "directions",
        "is_open_access", "landing_url", "pdf_url", "abstract",
    ]
    queue_rows = [
        {
            "screening_rank": str(rank),
            "canonical_paper_id": f"doi:{rank}",
            "title": f"Paper {rank}",
            "year": "2026",
            "authors": "A. Author",
            "venue": "Journal",
            "doi": f"10.1000/{rank}",
            "providers": "openalex",
            "provider_ids": f"openalex:W{rank}",
            "seed_ids": "P001",
            "dataset_names": "Dataset",
            "directions": "forward_citation",
            "is_open_access": "True",
            "abstract": "Agricultural semantic segmentation dataset and method.",
        }
        for rank in (1, 2)
    ]
    queue_path = repo / "outputs/screening_queue_2026-07-22/screening_queue.csv"
    write_csv(queue_path, queue_fields, queue_rows)
    history = repo / "data/curated/screening/title_abstract_decision_history.csv"
    active = repo / "data/curated/screening/title_abstract_decisions.csv"
    batches = repo / "data/curated/screening/screening_batches.csv"
    write_csv(history, CORE_FIELDS, [])
    write_csv(active, CORE_FIELDS, [])
    batch_fields = [
        "batch_id", "batch_type", "ranks", "protocol_version", "screened_at", "input_queue_path",
        "input_queue_sha256", "screened_rows_path", "screened_rows_sha256", "decision_count", "included",
        "excluded", "unclear", "provenance_status", "quality_gates_passed", "notes",
    ]
    write_csv(batches, batch_fields, [])
    (repo / "docs/project").mkdir(parents=True)

    prep = subprocess.run(
        [sys.executable, str(ROOT / "scripts/research/prepare_screening_batch.py"), "--repo", str(repo), "--ranks", "1-2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert prep.returncode == 0, prep.stdout + prep.stderr
    batch_dir = repo / "outputs/screening_batches/batch_001_ranks_1-2"
    manifest = json.loads((batch_dir / "batch_manifest.json").read_text())
    with (batch_dir / "screened_rows_template.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row.update({
            "decision": "include",
            "decision_confidence": "high",
            "reason_code": "I05",
            "reason_note": "Agricultural segmentation method",
            "likely_paper_type": "method_paper",
            "likely_dataset_relationship": "uses_dataset_experimentally",
            "named_datasets": "Dataset",
            "agricultural_domain": "crop",
            "vision_task": "semantic_segmentation",
            "modalities": "RGB",
            "relevance_yes": "semantic_segmentation",
            "relevance_unclear": "",
            "model": "test-model",
            "screened_at": "2026-07-22T00:00:00Z",
        })
    write_csv(batch_dir / "screened_rows.csv", CORE_FIELDS, rows)

    final = subprocess.run(
        [sys.executable, str(ROOT / "scripts/research/finalize_screening_batch.py"), str(batch_dir), "--repo", str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert final.returncode == 0, final.stdout + final.stderr
    with active.open(encoding="utf-8", newline="") as handle:
        active_rows = list(csv.DictReader(handle))
    assert len(active_rows) == 2
    assert json.loads((batch_dir / "batch_manifest.json").read_text())["status"] == "finalized"
    assert manifest["source_queue_sha256"] == active_rows[0]["source_queue_sha256"]


def test_finalize_duplicate_batch_does_not_mutate_history(tmp_path: Path) -> None:
    repo = tmp_path
    queue_fields = [
        "screening_rank", "canonical_paper_id", "title", "year", "authors", "venue", "doi", "arxiv_id",
        "pmid", "pmcid", "providers", "provider_ids", "seed_ids", "dataset_names", "directions",
        "is_open_access", "landing_url", "pdf_url", "abstract",
    ]
    queue_rows = [{
        "screening_rank": "1", "canonical_paper_id": "doi:1", "title": "Paper 1", "year": "2026",
        "authors": "A. Author", "venue": "Journal", "doi": "10.1000/1", "providers": "openalex",
        "provider_ids": "openalex:W1", "seed_ids": "P001", "dataset_names": "Dataset",
        "directions": "forward_citation", "is_open_access": "True",
        "abstract": "Agricultural semantic segmentation dataset and method.",
    }]
    queue_path = repo / "outputs/screening_queue_2026-07-22/screening_queue.csv"
    write_csv(queue_path, queue_fields, queue_rows)
    history = repo / "data/curated/screening/title_abstract_decision_history.csv"
    active = repo / "data/curated/screening/title_abstract_decisions.csv"
    batches = repo / "data/curated/screening/screening_batches.csv"
    write_csv(history, CORE_FIELDS, [])
    write_csv(active, CORE_FIELDS, [])
    batch_fields = [
        "batch_id", "batch_type", "ranks", "protocol_version", "screened_at", "input_queue_path",
        "input_queue_sha256", "screened_rows_path", "screened_rows_sha256", "decision_count", "included",
        "excluded", "unclear", "provenance_status", "quality_gates_passed", "notes",
    ]
    write_csv(batches, batch_fields, [{
        "batch_id": "B001", "batch_type": "title_abstract", "ranks": "legacy",
        "protocol_version": "AI_SCREENING_V1", "screened_at": "2026-07-22T00:00:00Z",
        "input_queue_path": "x", "input_queue_sha256": "x", "screened_rows_path": "x",
        "screened_rows_sha256": "x", "decision_count": "0", "included": "0", "excluded": "0",
        "unclear": "0", "provenance_status": "test", "quality_gates_passed": "true", "notes": "",
    }])
    (repo / "docs/project").mkdir(parents=True)

    prep = subprocess.run(
        [sys.executable, str(ROOT / "scripts/research/prepare_screening_batch.py"), "--repo", str(repo), "--ranks", "1"],
        capture_output=True, text=True, check=False,
    )
    # The preparer selects B002 because B001 already exists, so rewrite the
    # manifest deliberately to simulate a conflicting finalization target.
    assert prep.returncode == 0, prep.stdout + prep.stderr
    batch_dir = repo / "outputs/screening_batches/batch_002_ranks_1-1"
    manifest_path = batch_dir / "batch_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["batch_id"] = "B001"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with (batch_dir / "screened_rows_template.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0].update({
        "batch_id": "B001", "decision": "include", "decision_confidence": "high", "reason_code": "I05",
        "reason_note": "Agricultural segmentation method", "likely_paper_type": "method_paper",
        "likely_dataset_relationship": "uses_dataset_experimentally", "named_datasets": "Dataset",
        "agricultural_domain": "crop", "vision_task": "semantic_segmentation", "modalities": "RGB",
        "relevance_yes": "semantic_segmentation", "model": "test-model",
        "screened_at": "2026-07-22T00:00:00Z",
    })
    write_csv(batch_dir / "screened_rows.csv", CORE_FIELDS, rows)
    before = history.read_bytes()
    final = subprocess.run(
        [sys.executable, str(ROOT / "scripts/research/finalize_screening_batch.py"), str(batch_dir), "--repo", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert final.returncode == 2
    assert history.read_bytes() == before
    assert "Batch provenance already contains B001" in final.stdout
