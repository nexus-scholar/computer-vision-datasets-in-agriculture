from pathlib import Path

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import atomic_write_csv, read_csv, sha256_file
from agri_fulltext.reviewing import finalize_review, prepare_review
from agri_fulltext.schema import ARTIFACT_REGISTRY_FIELDS, EXTRACTION_REGISTRY_FIELDS, FULLTEXT_DECISION_FIELDS


def _repo(tmp_path: Path) -> tuple[Path, object]:
    repo = tmp_path / "repo"
    settings = load_settings(repo)
    paper_dir = repo / "outputs/fulltext/processing/run/p1"
    (paper_dir / "llm").mkdir(parents=True)
    (paper_dir / "llm/paper.md").write_text("# Paper\n\nEvidence text", encoding="utf-8")
    (paper_dir / "llm/chunks.jsonl").write_text('{"text":"Evidence text"}\n', encoding="utf-8")
    (paper_dir / "manifest.json").write_text('{}\n', encoding="utf-8")
    source = repo / "data/raw/fulltext/p1/hash/source.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    atomic_write_csv(settings.artifact_registry, ARTIFACT_REGISTRY_FIELDS, [{
        "artifact_id": "a1", "paper_id": "p1", "rank": "1", "title": "Paper", "source": "manual",
        "artifact_type": "pdf", "stored_path": str(source.relative_to(repo)), "sha256": sha256_file(source),
        "size_bytes": source.stat().st_size, "mime_type": "application/pdf", "source_url": "", "final_url": "",
        "license": "", "version": "user_supplied", "host_type": "local", "rights_status": "local_research_only",
        "acquired_at": "2026-01-01T00:00:00Z", "run_id": "r1", "candidate_id": "", "status": "success", "notes": "",
    }])
    atomic_write_csv(settings.extraction_registry, EXTRACTION_REGISTRY_FIELDS, [{
        "extraction_id": "e1", "paper_id": "p1", "rank": "1", "title": "Paper", "source_sha256": sha256_file(source),
        "source_artifact_type": "pdf", "output_dir": str(paper_dir.relative_to(repo)), "docling_status": "success",
        "grobid_status": "success", "publisher_xml_status": "not_available", "preflight_class": "born_digital",
        "qa_status": "manual_review", "processor_version": "0.1.0", "created_at": "2026-01-01T00:00:00Z",
        "run_id": "r2", "manifest_sha256": sha256_file(paper_dir / "manifest.json"), "notes": "",
    }])
    return repo, settings


def test_prepare_and_finalize_review(tmp_path: Path):
    repo, settings = _repo(tmp_path)
    workspace = prepare_review(settings, "1", repo / "outputs/fulltext/reviews/test")
    fields, rows = read_csv(workspace / "decision_template.csv")
    assert fields == FULLTEXT_DECISION_FIELDS
    row = rows[0]
    row.update({
        "decision": "include_core",
        "reason_code": "FI02_ACTUAL_DATASET_USE",
        "paper_role": "method_paper",
        "actual_dataset_use": "yes",
        "dataset_relationship": "used_evaluation",
        "named_datasets": "Dataset X",
        "evidence_summary": "The paper evaluates on Dataset X.",
        "source_page": "4",
        "source_section": "Experiments",
        "reviewer": "opencode_ai",
    })
    decision = workspace / "decision.csv"
    atomic_write_csv(decision, FULLTEXT_DECISION_FIELDS, [row])
    result = finalize_review(settings, decision)
    assert result["decision"] == "include_core"
    _, saved = read_csv(repo / "data/curated/screening/full_text_decisions.csv")
    assert len(saved) == 1
    assert saved[0]["dataset_relationship"] == "used_evaluation"
