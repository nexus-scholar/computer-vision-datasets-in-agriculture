from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .io_utils import append_csv, atomic_write_csv, now_utc, read_csv, safe_segment, sha256_file, sha256_text, timestamp_id, write_json
from .schema import FULLTEXT_DECISION_FIELDS

DECISIONS = {"include_core", "include_supporting", "exclude", "unresolved"}
RELATIONSHIPS = {
    "introduced",
    "used_training",
    "used_evaluation",
    "used_pretraining",
    "extended",
    "repackaged",
    "benchmarked",
    "compared_descriptively",
    "mentioned_only",
    "unclear",
}
ACTUAL_USE = {"yes", "no", "unclear"}
REASON_PREFIXES = {
    "include_core": ("FI",),
    "include_supporting": ("FS",),
    "exclude": ("FE",),
    "unresolved": ("FU",),
}


def prepare_review(settings: Settings, identifier: str, out_dir: Path | None = None) -> Path:
    extraction = _find_extraction(settings, identifier)
    output_dir = settings.repo / extraction["output_dir"]
    if not output_dir.exists():
        raise ValueError(f"Extraction output does not exist: {output_dir}")
    rank = int(extraction.get("rank") or 0)
    paper_id = extraction.get("paper_id", "")
    out_dir = out_dir or (settings.repo / "outputs/fulltext/reviews" / f"review_{rank:04d}_{timestamp_id()}")
    out_dir.mkdir(parents=True, exist_ok=False)
    context = {
        "paper_id": paper_id,
        "rank": rank,
        "title": extraction.get("title", ""),
        "extraction_id": extraction.get("extraction_id", ""),
        "qa_status": extraction.get("qa_status", ""),
        "preflight_class": extraction.get("preflight_class", ""),
        "output_dir": extraction.get("output_dir", ""),
        "paper_markdown": _relative(settings, output_dir / "llm/paper.md"),
        "chunks_jsonl": _relative(settings, output_dir / "llm/chunks.jsonl"),
        "references_jsonl": _relative(settings, output_dir / "llm/references.jsonl"),
        "citation_contexts_jsonl": _relative(settings, output_dir / "llm/citation_contexts.jsonl"),
        "tables_jsonl": _relative(settings, output_dir / "llm/tables.jsonl"),
        "figures_jsonl": _relative(settings, output_dir / "llm/figures.jsonl"),
        "formulas_jsonl": _relative(settings, output_dir / "llm/formulas.jsonl"),
        "docling_json": _relative(settings, output_dir / "docling/normalized/document.json"),
        "docling_html": _relative(settings, output_dir / "docling/normalized/document.html"),
        "source_pdf": _source_pdf(settings, paper_id),
        "extraction_manifest": _relative(settings, output_dir / "manifest.json"),
        "extraction_manifest_sha256": sha256_file(output_dir / "manifest.json") if (output_dir / "manifest.json").exists() else "",
        "prepared_at": now_utc(),
    }
    write_json(out_dir / "review_context.json", context)
    template = {field: "" for field in FULLTEXT_DECISION_FIELDS}
    template.update(
        {
            "paper_id": paper_id,
            "rank": rank,
            "title": extraction.get("title", ""),
            "extraction_id": extraction.get("extraction_id", ""),
            "actual_dataset_use": "unclear",
            "dataset_relationship": "unclear",
            "named_datasets": "unknown",
            "source_page": "unknown",
            "source_section": "unknown",
            "source_table": "unknown",
            "source_figure": "unknown",
            "reviewer": "opencode_ai",
            "notes": f"review_context:{_relative(settings, out_dir / 'review_context.json')}",
        }
    )
    atomic_write_csv(out_dir / "decision_template.csv", FULLTEXT_DECISION_FIELDS, [template])
    write_json(
        out_dir / "review_manifest.json",
        {
            "paper_id": paper_id,
            "rank": rank,
            "extraction_id": extraction.get("extraction_id", ""),
            "extraction_registry": str(settings.extraction_registry),
            "extraction_registry_sha256": sha256_file(settings.extraction_registry),
            "decision_target": "data/curated/screening/full_text_decisions.csv",
            "prepared_at": now_utc(),
        },
    )
    return out_dir


def finalize_review(settings: Settings, decision_path: Path) -> dict[str, Any]:
    fields, rows = read_csv(decision_path)
    if fields != FULLTEXT_DECISION_FIELDS:
        raise ValueError(f"Decision schema mismatch: {fields}")
    if len(rows) != 1:
        raise ValueError("A full-text review decision file must contain exactly one data row")
    row = {key: (value or "").strip() for key, value in rows[0].items()}
    extraction = _find_extraction(settings, row.get("paper_id", "") or row.get("rank", ""))
    for key in ("paper_id", "rank", "title", "extraction_id"):
        expected = str(extraction.get(key, "")).strip()
        if row.get(key, "") != expected:
            raise ValueError(f"{key} does not match the active extraction: {row.get(key)!r} != {expected!r}")
    decision = row.get("decision", "")
    if decision not in DECISIONS:
        raise ValueError(f"Invalid full-text decision: {decision}")
    reason = row.get("reason_code", "")
    if not reason or not reason.startswith(REASON_PREFIXES[decision]):
        raise ValueError(f"Reason code {reason!r} is incompatible with {decision}")
    if row.get("actual_dataset_use", "") not in ACTUAL_USE:
        raise ValueError("actual_dataset_use must be yes, no, or unclear")
    if row.get("dataset_relationship", "") not in RELATIONSHIPS:
        raise ValueError(f"Invalid dataset relationship: {row.get('dataset_relationship')}")
    if decision in {"include_core", "include_supporting"} and not row.get("evidence_summary", ""):
        raise ValueError("Included papers require an evidence_summary")
    if row.get("actual_dataset_use") == "yes" and all(
        row.get(field, "") in {"", "unknown"}
        for field in ("source_page", "source_section", "source_table", "source_figure")
    ):
        raise ValueError("Actual dataset use requires at least one source locator")
    if not row.get("reviewer", ""):
        raise ValueError("reviewer is required")
    if not row.get("reviewed_at", ""):
        row["reviewed_at"] = now_utc()

    _, existing = read_csv(settings.repo / "data/curated/screening/full_text_decisions.csv")
    active = [item for item in existing if item.get("paper_id") == row["paper_id"]]
    latest = active[-1] if active else None
    supersedes = row.get("supersedes_fulltext_screening_id", "")
    if latest and supersedes != latest.get("fulltext_screening_id", ""):
        raise ValueError(
            "This paper already has a full-text decision; a correction must explicitly supersede "
            f"{latest.get('fulltext_screening_id', '')}"
        )
    if not latest and supersedes:
        raise ValueError("supersedes_fulltext_screening_id was provided but no earlier decision exists")
    if not row.get("fulltext_screening_id"):
        row["fulltext_screening_id"] = "FTS_" + sha256_text(
            f"{row['paper_id']}|{row['extraction_id']}|{row['reviewed_at']}|{decision}"
        )[:20]
    if any(item.get("fulltext_screening_id") == row["fulltext_screening_id"] for item in existing):
        raise ValueError(f"Duplicate fulltext_screening_id: {row['fulltext_screening_id']}")
    append_csv(
        settings.repo / "data/curated/screening/full_text_decisions.csv",
        FULLTEXT_DECISION_FIELDS,
        [row],
    )
    return {
        "fulltext_screening_id": row["fulltext_screening_id"],
        "paper_id": row["paper_id"],
        "rank": int(row["rank"]),
        "decision": decision,
        "dataset_relationship": row["dataset_relationship"],
        "actual_dataset_use": row["actual_dataset_use"],
        "reviewed_at": row["reviewed_at"],
    }


def _find_extraction(settings: Settings, identifier: str) -> dict[str, str]:
    _, rows = read_csv(settings.extraction_registry)
    matches = [
        row
        for row in rows
        if row.get("paper_id") == str(identifier) or row.get("rank") == str(identifier)
    ]
    if not matches:
        raise ValueError(f"No processed paper matches {identifier!r}")
    return sorted(matches, key=lambda item: item.get("created_at", ""))[-1]


def _relative(settings: Settings, path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return str(path.relative_to(settings.repo)).replace("\\", "/")
    except ValueError:
        return str(path)


def _source_pdf(settings: Settings, paper_id: str) -> str:
    _, rows = read_csv(settings.artifact_registry)
    matches = [
        row
        for row in rows
        if row.get("paper_id") == paper_id
        and row.get("artifact_type") == "pdf"
        and row.get("status") == "success"
    ]
    if not matches:
        return ""
    return sorted(matches, key=lambda item: item.get("acquired_at", ""))[-1].get("stored_path", "")
