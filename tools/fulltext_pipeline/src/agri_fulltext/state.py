from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lxml import etree

from .config import Settings
from .io_utils import atomic_write_csv, now_utc, read_csv, sha256_file, timestamp_id, write_json


def fulltext_status(settings: Settings) -> dict[str, Any]:
    _, artifacts = read_csv(settings.artifact_registry)
    _, attempts = read_csv(settings.attempt_registry)
    _, resolver_errors = read_csv(settings.resolver_error_registry)
    _, extractions = read_csv(settings.extraction_registry)
    _, decisions = read_csv(settings.decisions_path)
    eligible = [row for row in decisions if row.get("decision") in {"include", "unclear"}]
    successful_artifacts = [row for row in artifacts if row.get("status") == "success"]
    papers_with_artifacts = {row.get("paper_id", "") for row in successful_artifacts}
    papers_with_pdf = {row.get("paper_id", "") for row in successful_artifacts if row.get("artifact_type") == "pdf"}
    papers_with_xml = {
        row.get("paper_id", "") for row in successful_artifacts if row.get("artifact_type") in {"jats_xml", "tei_xml", "xml"}
    }
    active_extractions: dict[str, dict[str, str]] = {}
    for row in extractions:
        paper_id = row.get("paper_id", "")
        if paper_id not in active_extractions or row.get("created_at", "") >= active_extractions[paper_id].get("created_at", ""):
            active_extractions[paper_id] = row
    return {
        "eligible_title_abstract_records": len(eligible),
        "papers_with_any_artifact": len(papers_with_artifacts),
        "papers_with_pdf": len(papers_with_pdf),
        "papers_with_structured_xml": len(papers_with_xml),
        "artifact_rows": len(successful_artifacts),
        "processed_papers": len(active_extractions),
        "qa_status_counts": dict(Counter(row.get("qa_status", "unknown") for row in active_extractions.values())),
        "source_counts": dict(Counter(row.get("source", "unknown") for row in successful_artifacts)),
        "rights_counts": dict(Counter(row.get("rights_status", "unknown") for row in successful_artifacts)),
        "fetch_attempt_count": len(attempts),
        "fetch_attempt_status_counts": dict(Counter(row.get("status", "unknown") for row in attempts)),
        "resolver_error_count": len(resolver_errors),
        "pending_acquisition": max(0, len(eligible) - len(papers_with_artifacts)),
        "pending_processing": max(0, len(papers_with_artifacts) - len(active_extractions)),
    }


def validate_fulltext(settings: Settings) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    _, artifacts = read_csv(settings.artifact_registry)
    seen_artifacts: set[str] = set()
    for row in artifacts:
        artifact_id = row.get("artifact_id", "")
        if not artifact_id:
            errors.append("Artifact row missing artifact_id")
        elif artifact_id in seen_artifacts:
            errors.append(f"Duplicate artifact_id: {artifact_id}")
        seen_artifacts.add(artifact_id)
        if row.get("status") != "success":
            continue
        path = settings.repo / row.get("stored_path", "")
        if not path.exists():
            errors.append(f"Missing stored artifact: {row.get('stored_path')}")
            continue
        actual_sha = sha256_file(path)
        if actual_sha != row.get("sha256"):
            errors.append(f"SHA mismatch: {row.get('stored_path')}")
        if row.get("artifact_type") == "pdf":
            with path.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    errors.append(f"Invalid PDF signature: {row.get('stored_path')}")
        else:
            try:
                etree.parse(str(path))
            except Exception as exc:
                errors.append(f"Invalid XML {row.get('stored_path')}: {exc}")
        if row.get("rights_status") in {"restricted", "local_research_only"} and path.is_relative_to(settings.repo):
            warnings.append(f"Restricted/local-only artifact must remain ignored by Git: {row.get('stored_path')}")

    _, attempts = read_csv(settings.attempt_registry)
    seen_attempts: set[str] = set()
    for row in attempts:
        attempt_id = row.get("attempt_id", "")
        if not attempt_id:
            errors.append("Fetch-attempt row missing attempt_id")
        elif attempt_id in seen_attempts:
            errors.append(f"Duplicate attempt_id: {attempt_id}")
        seen_attempts.add(attempt_id)
        url = row.get("url", "").lower()
        if any(token in url for token in ("api_key=", "apikey=", "email=", "token=", "access_token=", "signature=", "x-amz-signature=")) and "redacted" not in url:
            errors.append(f"Unredacted secret-bearing fetch URL: {attempt_id}")

    _, resolver_errors = read_csv(settings.resolver_error_registry)
    seen_resolver_errors: set[str] = set()
    for row in resolver_errors:
        error_id = row.get("error_id", "")
        if not error_id:
            errors.append("Resolver-error row missing error_id")
        elif error_id in seen_resolver_errors:
            errors.append(f"Duplicate resolver error_id: {error_id}")
        seen_resolver_errors.add(error_id)

    _, extractions = read_csv(settings.extraction_registry)
    seen_extractions: set[str] = set()
    for row in extractions:
        extraction_id = row.get("extraction_id", "")
        if not extraction_id:
            errors.append("Extraction row missing extraction_id")
        elif extraction_id in seen_extractions:
            errors.append(f"Duplicate extraction_id: {extraction_id}")
        seen_extractions.add(extraction_id)
        output_dir = settings.repo / row.get("output_dir", "")
        manifest = output_dir / "manifest.json"
        if not output_dir.exists():
            errors.append(f"Missing extraction output: {row.get('output_dir')}")
        elif not manifest.exists():
            errors.append(f"Missing extraction manifest: {manifest}")
        elif row.get("manifest_sha256") and sha256_file(manifest) != row.get("manifest_sha256"):
            errors.append(f"Extraction manifest SHA mismatch: {manifest}")
        if row.get("qa_status") == "pass" and not (output_dir / "llm/chunks.jsonl").exists():
            errors.append(f"QA pass without LLM chunks: {output_dir}")

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "artifact_count": len(artifacts),
        "fetch_attempt_count": len(attempts),
        "resolver_error_count": len(resolver_errors),
        "extraction_count": len(extractions),
        "checked_at": now_utc(),
    }


def build_review_queue(settings: Settings, out_dir: Path | None = None) -> Path:
    _, extraction_rows = read_csv(settings.extraction_registry)
    active: dict[str, dict[str, str]] = {}
    for row in extraction_rows:
        paper_id = row.get("paper_id", "")
        if paper_id not in active or row.get("created_at", "") >= active[paper_id].get("created_at", ""):
            active[paper_id] = row
    rows = []
    for row in sorted(active.values(), key=lambda item: int(item.get("rank") or 0)):
        output_dir = settings.repo / row.get("output_dir", "")
        llm_dir = output_dir / "llm"
        rows.append(
            {
                "paper_id": row.get("paper_id", ""),
                "rank": row.get("rank", ""),
                "title": row.get("title", ""),
                "extraction_id": row.get("extraction_id", ""),
                "qa_status": row.get("qa_status", ""),
                "preflight_class": row.get("preflight_class", ""),
                "paper_markdown": _relative(settings, llm_dir / "paper.md"),
                "chunks_jsonl": _relative(settings, llm_dir / "chunks.jsonl"),
                "references_jsonl": _relative(settings, llm_dir / "references.jsonl"),
                "tables_jsonl": _relative(settings, llm_dir / "tables.jsonl"),
                "figures_jsonl": _relative(settings, llm_dir / "figures.jsonl"),
                "formulas_jsonl": _relative(settings, llm_dir / "formulas.jsonl"),
                "source_pdf": _source_pdf(settings, row.get("paper_id", "")),
                "full_text_decision": "",
                "paper_role": "",
                "actual_dataset_use": "",
                "dataset_use_evidence": "",
                "reviewer": "",
                "reviewed_at": "",
                "notes": "",
            }
        )
    out_dir = out_dir or (settings.repo / "outputs/fulltext" / f"review_queue_{timestamp_id()}")
    out_dir.mkdir(parents=True, exist_ok=False)
    fields = list(rows[0].keys()) if rows else [
        "paper_id", "rank", "title", "extraction_id", "qa_status", "preflight_class", "paper_markdown",
        "chunks_jsonl", "references_jsonl", "tables_jsonl", "figures_jsonl", "formulas_jsonl", "source_pdf", "full_text_decision",
        "paper_role", "actual_dataset_use", "dataset_use_evidence", "reviewer", "reviewed_at", "notes",
    ]
    queue_path = out_dir / "fulltext_review_queue.csv"
    atomic_write_csv(queue_path, fields, rows)
    write_json(
        out_dir / "queue_manifest.json",
        {
            "created_at": now_utc(),
            "extraction_registry": str(settings.extraction_registry),
            "extraction_registry_sha256": sha256_file(settings.extraction_registry),
            "paper_count": len(rows),
        },
    )
    return queue_path


def _relative(settings: Settings, path: Path) -> str:
    if not path.exists():
        return ""
    return str(path.relative_to(settings.repo)).replace("\\", "/")


def _source_pdf(settings: Settings, paper_id: str) -> str:
    _, rows = read_csv(settings.artifact_registry)
    matches = [row for row in rows if row.get("paper_id") == paper_id and row.get("artifact_type") == "pdf" and row.get("status") == "success"]
    if not matches:
        return ""
    row = sorted(matches, key=lambda item: item.get("acquired_at", ""))[-1]
    return row.get("stored_path", "")
