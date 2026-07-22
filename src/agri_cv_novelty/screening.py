from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

CORE_FIELDS = [
    "screening_id",
    "candidate_id",
    "rank",
    "title",
    "decision",
    "decision_confidence",
    "reason_code",
    "reason_note",
    "likely_paper_type",
    "likely_dataset_relationship",
    "named_datasets",
    "agricultural_domain",
    "vision_task",
    "modalities",
    "relevance_yes",
    "relevance_unclear",
    "abstract_available",
    "full_text_available",
    "identity_status",
    "reviewer",
    "model",
    "protocol_version",
    "screened_at",
    "batch_id",
    "source_queue_sha256",
    "supersedes_screening_id",
    "notes",
]

RELEVANCE_TAGS = [
    "semantic_segmentation",
    "instance_segmentation",
    "panoptic_segmentation",
    "object_detection",
    "classification",
    "tracking",
    "phenotyping",
    "3d_vision",
    "remote_sensing",
    "uav",
    "robotics",
    "multispectral",
    "hyperspectral",
    "thermal",
    "depth_or_rgbd",
    "lidar_or_point_cloud",
    "multimodal",
    "multitemporal",
    "domain_adaptation",
    "cross_sensor",
    "missing_modality",
    "corrupted_input",
    "uncertainty",
    "calibration",
    "failure_detection",
    "foundation_models",
]

WIDE_RELEVANCE_FIELDS = ["screening_id", "candidate_id", "rank", *[f"relevant_{tag}" for tag in RELEVANCE_TAGS]]

QUEUE_ENRICHMENT_FIELDS = [
    "year", "publication_date", "authors", "venue", "journal", "doi", "arxiv_id", "pmid", "pmcid",
    "providers", "provider_ids", "source_seed_ids", "source_directions", "queue_dataset_names",
    "priority_score", "is_open_access", "landing_url", "pdf_url",
]
ENRICHED_FIELDS = [
    *CORE_FIELDS,
    *QUEUE_ENRICHMENT_FIELDS,
    *[field for field in WIDE_RELEVANCE_FIELDS if field not in {"screening_id", "candidate_id", "rank"}],
]

ALLOWED_DECISIONS = {"include", "exclude", "unclear"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_TERNARY = {"yes", "no", "unknown"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if any(None in row for row in rows):
            bad = [str(index + 2) for index, row in enumerate(rows) if None in row]
            raise ValueError(f"Malformed CSV rows with excess columns in {path}: lines {', '.join(bad)}")
        return list(reader.fieldnames or []), rows


def atomic_write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with temp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        temp.replace(path)
        path.chmod(0o644)
    finally:
        if temp.exists():
            temp.unlink()


def split_tags(value: str) -> set[str]:
    return {part.strip() for part in (value or "").split(";") if part.strip()}


def validate_decision_row(row: dict[str, str], *, line_label: str = "row") -> list[str]:
    errors: list[str] = []
    for field in CORE_FIELDS:
        if field not in row:
            errors.append(f"{line_label}: missing field {field}")
    for field in (
        "screening_id", "candidate_id", "rank", "title", "decision", "decision_confidence", "reason_code",
        "reviewer", "model", "protocol_version", "screened_at", "batch_id", "source_queue_sha256",
    ):
        if not (row.get(field) or "").strip():
            errors.append(f"{line_label}: required value is blank: {field}")

    screening_id = (row.get("screening_id") or "").strip()
    if screening_id and not re.fullmatch(r"TA_R\d{4}(?:_[A-Z0-9]+)?", screening_id):
        errors.append(f"{line_label}: invalid screening_id format: {screening_id!r}")
    batch_id = (row.get("batch_id") or "").strip()
    if batch_id and not re.fullmatch(r"(?:B|QA)\d{3}", batch_id):
        errors.append(f"{line_label}: invalid batch_id format: {batch_id!r}")
    queue_sha = (row.get("source_queue_sha256") or "").strip()
    if queue_sha and not re.fullmatch(r"[0-9a-f]{64}", queue_sha):
        errors.append(f"{line_label}: source_queue_sha256 must be lowercase SHA-256")
    if (row.get("protocol_version") or "").strip() != "AI_SCREENING_V1":
        errors.append(f"{line_label}: unsupported protocol_version {row.get('protocol_version')!r}")
    timestamp = (row.get("screened_at") or "").strip()
    if timestamp:
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{line_label}: screened_at is not an ISO-8601 timestamp: {timestamp!r}")

    decision = (row.get("decision") or "").strip()
    confidence = (row.get("decision_confidence") or "").strip()
    reason_codes = [code.strip() for code in (row.get("reason_code") or "").split(";") if code.strip()]
    if decision not in ALLOWED_DECISIONS:
        errors.append(f"{line_label}: invalid decision {decision!r}")
    if confidence not in ALLOWED_CONFIDENCE:
        errors.append(f"{line_label}: invalid confidence {confidence!r}")
    if decision == "exclude" and confidence == "low":
        errors.append(f"{line_label}: low-confidence exclusions are not allowed")
    expected_prefix = {"include": "I", "exclude": "E", "unclear": "U"}.get(decision)
    if expected_prefix and (not reason_codes or any(not code.startswith(expected_prefix) for code in reason_codes)):
        errors.append(f"{line_label}: reason codes do not match decision {decision!r}: {reason_codes}")

    try:
        rank = int(row.get("rank", ""))
        if rank < 1:
            errors.append(f"{line_label}: rank must be positive")
    except ValueError:
        errors.append(f"{line_label}: rank is not an integer: {row.get('rank')!r}")

    yes = split_tags(row.get("relevance_yes", ""))
    unclear = split_tags(row.get("relevance_unclear", ""))
    unknown_tags = (yes | unclear) - set(RELEVANCE_TAGS)
    if unknown_tags:
        errors.append(f"{line_label}: unknown relevance tags: {sorted(unknown_tags)}")
    overlap = yes & unclear
    if overlap:
        errors.append(f"{line_label}: tags cannot be both yes and unclear: {sorted(overlap)}")

    for field in ("abstract_available", "full_text_available"):
        value = (row.get(field) or "").strip()
        if value and value not in ALLOWED_TERNARY:
            errors.append(f"{line_label}: {field} must be yes/no/unknown, got {value!r}")
    return errors


def validate_history(rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    errors: list[str] = []
    seen_ids: dict[str, dict[str, str]] = {}
    active_by_candidate: dict[str, dict[str, str]] = {}

    for index, row in enumerate(rows, start=2):
        label = f"history line {index}"
        errors.extend(validate_decision_row(row, line_label=label))
        screening_id = (row.get("screening_id") or "").strip()
        candidate_id = (row.get("candidate_id") or "").strip()
        if screening_id in seen_ids:
            errors.append(f"{label}: duplicate screening_id {screening_id}")
            continue

        previous = active_by_candidate.get(candidate_id)
        supersedes = (row.get("supersedes_screening_id") or "").strip()
        if previous:
            if not supersedes:
                errors.append(f"{label}: repeated candidate {candidate_id} lacks supersedes_screening_id")
            elif supersedes != previous.get("screening_id"):
                errors.append(
                    f"{label}: supersedes {supersedes}, but active event is {previous.get('screening_id')}"
                )
            if row.get("rank") != previous.get("rank"):
                errors.append(f"{label}: correction changed rank for {candidate_id}")
        elif supersedes:
            errors.append(f"{label}: supersedes unknown event {supersedes}")

        seen_ids[screening_id] = row
        active_by_candidate[candidate_id] = row

    active = sorted(active_by_candidate.values(), key=lambda row: int(row["rank"])) if not errors else []
    ranks = [int(row["rank"]) for row in active] if active else []
    if len(ranks) != len(set(ranks)):
        errors.append("Active decisions contain duplicate ranks")
    return errors, active


def build_relevance_rows(active_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in active_rows:
        yes = split_tags(row.get("relevance_yes", ""))
        unclear = split_tags(row.get("relevance_unclear", ""))
        out = {
            "screening_id": row["screening_id"],
            "candidate_id": row["candidate_id"],
            "rank": row["rank"],
        }
        for tag in RELEVANCE_TAGS:
            out[f"relevant_{tag}"] = "yes" if tag in yes else ("unclear" if tag in unclear else "no")
        rows.append(out)
    return rows


def build_enriched_rows(
    active_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    queue_by_rank = {str(row.get("screening_rank", "")): row for row in queue_rows}
    relevance_by_candidate = {
        row["candidate_id"]: row for row in build_relevance_rows(active_rows)
    }
    rows: list[dict[str, str]] = []
    for active in active_rows:
        queue = queue_by_rank.get(active["rank"], {})
        out = {field: active.get(field, "") for field in CORE_FIELDS}
        out.update({
            "year": queue.get("year", ""),
            "publication_date": queue.get("publication_date", ""),
            "authors": queue.get("authors", ""),
            "venue": queue.get("venue", ""),
            "journal": queue.get("journal", ""),
            "doi": queue.get("doi", ""),
            "arxiv_id": queue.get("arxiv_id", ""),
            "pmid": queue.get("pmid", ""),
            "pmcid": queue.get("pmcid", ""),
            "providers": queue.get("providers", ""),
            "provider_ids": queue.get("provider_ids", ""),
            "source_seed_ids": queue.get("seed_ids", ""),
            "source_directions": queue.get("directions", ""),
            "queue_dataset_names": queue.get("dataset_names", ""),
            "priority_score": queue.get("priority_score", ""),
            "is_open_access": queue.get("is_open_access", ""),
            "landing_url": queue.get("landing_url", ""),
            "pdf_url": queue.get("pdf_url", ""),
        })
        relevance = relevance_by_candidate.get(active["candidate_id"], {})
        for field in WIDE_RELEVANCE_FIELDS:
            if field not in {"screening_id", "candidate_id", "rank"}:
                out[field] = relevance.get(field, "")
        rows.append(out)
    return rows


def compare_rows(expected: list[dict[str, str]], actual: list[dict[str, str]], fields: list[str]) -> list[str]:
    errors: list[str] = []
    if len(expected) != len(actual):
        errors.append(f"Row-count mismatch: expected {len(expected)}, found {len(actual)}")
        return errors
    for index, (left, right) in enumerate(zip(expected, actual), start=2):
        for field in fields:
            if (left.get(field) or "") != (right.get(field) or ""):
                errors.append(
                    f"Line {index}: field {field} differs: expected {left.get(field)!r}, found {right.get(field)!r}"
                )
                if len(errors) >= 30:
                    return errors
    return errors


def validate_against_queue(
    active_rows: list[dict[str, str]],
    queue_rows: list[dict[str, str]],
    *,
    queue_sha256: str | None = None,
) -> list[str]:
    errors: list[str] = []
    queue_by_rank = {str(row.get("screening_rank", "")): row for row in queue_rows}
    for row in active_rows:
        queue = queue_by_rank.get(row["rank"])
        if not queue:
            errors.append(f"Rank {row['rank']} does not exist in the queue")
            continue
        if row["candidate_id"] != queue.get("canonical_paper_id", ""):
            errors.append(f"Rank {row['rank']}: candidate_id does not match queue")
        if row["title"] != queue.get("title", ""):
            errors.append(f"Rank {row['rank']}: title does not match queue")
        if queue_sha256 and row.get("source_queue_sha256") != queue_sha256:
            errors.append(f"Rank {row['rank']}: source_queue_sha256 does not match frozen queue")
    return errors


def render_status(total_candidates: int, active_rows: list[dict[str, str]], *, updated_at: str | None = None) -> str:
    counts = Counter(row["decision"] for row in active_rows)
    ranks = sorted(int(row["rank"]) for row in active_rows)
    last_contiguous = 0
    for rank in ranks:
        if rank == last_contiguous + 1:
            last_contiguous = rank
        elif rank > last_contiguous + 1:
            break
    next_start = last_contiguous + 1
    next_end = min(total_candidates, next_start + 19)
    medium = [row["rank"] for row in active_rows if row.get("decision_confidence") == "medium"]
    missing_dataset = [
        row["rank"]
        for row in active_rows
        if row.get("decision") == "include"
        and row.get("likely_dataset_relationship")
        in {"uses_dataset_experimentally", "benchmarks_dataset", "extends_dataset", "pretrains_on_dataset"}
        and row.get("named_datasets") in {"", "unknown"}
    ]
    lines = [
        "# Screening status",
        "",
        "Status: AI-screened title/abstract decisions under a human-authorized protocol.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total canonical candidates | {total_candidates} |",
        f"| Active decisions | {len(active_rows)} |",
        f"| Included | {counts['include']} |",
        f"| Excluded | {counts['exclude']} |",
        f"| Unclear | {counts['unclear']} |",
        f"| Last contiguous rank | {last_contiguous} |",
        f"| Next recommended batch | {next_start}-{next_end} |" if next_start <= total_candidates else "| Next recommended batch | complete |",
        "| Protocol version | AI_SCREENING_V1 |",
        f"| Last updated | {updated_at or now_utc()} |",
        "",
        "## Active quality notes",
        "",
        "- The screening queue is frozen to preserve rank continuity; its accepted graph has known incomplete Semantic Scholar relations for P001 and P007.",
        f"- Medium-confidence active decisions: {', '.join(medium) if medium else 'none'}.",
        f"- Included experimental/benchmark rows with dataset name still unknown: {', '.join(missing_dataset) if missing_dataset else 'none'}.",
        "- Title/abstract screening is provisional. Actual dataset use and manuscript-grade claims require full-text evidence.",
    ]
    return "\n".join(lines) + "\n"


def write_active_state(
    *,
    history_path: Path,
    active_path: Path,
    relevance_path: Path,
    enriched_path: Path | None,
    queue_path: Path,
    status_path: Path,
) -> list[str]:
    fields, history = read_csv(history_path)
    errors: list[str] = []
    if fields != CORE_FIELDS:
        errors.append(f"History schema mismatch. Expected {CORE_FIELDS}, found {fields}")
    history_errors, active = validate_history(history)
    errors.extend(history_errors)
    if errors:
        return errors
    atomic_write_csv(active_path, CORE_FIELDS, active)
    atomic_write_csv(relevance_path, WIDE_RELEVANCE_FIELDS, build_relevance_rows(active))
    _, queue = read_csv(queue_path)
    if enriched_path is not None:
        atomic_write_csv(enriched_path, ENRICHED_FIELDS, build_enriched_rows(active, queue))
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(render_status(len(queue), active), encoding="utf-8")
    return []


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)
        path.chmod(0o644)
    finally:
        if temp.exists():
            temp.unlink()
