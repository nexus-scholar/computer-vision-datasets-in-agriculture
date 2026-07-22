#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agri_cv_novelty.screening import (  # noqa: E402
    CORE_FIELDS,
    atomic_write_csv,
    now_utc,
    read_csv,
    sha256_file,
    validate_decision_row,
    validate_history,
    write_active_state,
    write_json,
)

BATCH_FIELDS = [
    "batch_id", "batch_type", "ranks", "protocol_version", "screened_at", "input_queue_path",
    "input_queue_sha256", "screened_rows_path", "screened_rows_sha256", "decision_count", "included",
    "excluded", "unclear", "provenance_status", "quality_gates_passed", "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and atomically finalize one prepared screening batch.")
    parser.add_argument("batch_dir", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    args = parser.parse_args()
    repo = args.repo.resolve()
    batch_dir = args.batch_dir if args.batch_dir.is_absolute() else repo / args.batch_dir
    manifest_path = batch_dir / "batch_manifest.json"
    output_path = batch_dir / "screened_rows.csv"
    if not manifest_path.exists() or not output_path.exists():
        raise SystemExit("Batch manifest and screened_rows.csv are both required.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") == "finalized":
        raise SystemExit("Batch is already finalized.")

    fields, rows = read_csv(output_path)
    errors: list[str] = []
    if fields != CORE_FIELDS:
        errors.append(f"Output schema mismatch. Expected {CORE_FIELDS}, found {fields}")
    expected_ranks = [str(value) for value in manifest.get("requested_ranks", [])]
    if sorted((row.get("rank", "") for row in rows), key=int) != sorted(expected_ranks, key=int):
        errors.append(f"Output ranks do not match prepared ranks: expected {expected_ranks}")
    if len(rows) != len(expected_ranks):
        errors.append(f"Expected {len(expected_ranks)} rows, found {len(rows)}")

    input_fields, input_rows = read_csv(batch_dir / "input_rows.csv")
    del input_fields
    input_by_rank = {row["rank"]: row for row in input_rows}
    for index, row in enumerate(rows, start=2):
        errors.extend(validate_decision_row(row, line_label=f"screened_rows line {index}"))
        source = input_by_rank.get(row.get("rank", ""))
        if not source:
            continue
        if row.get("candidate_id") != source.get("candidate_id"):
            errors.append(f"Rank {row.get('rank')}: candidate_id changed from prepared input")
        if row.get("title") != source.get("title"):
            errors.append(f"Rank {row.get('rank')}: title changed from prepared input")
        if row.get("batch_id") != manifest.get("batch_id"):
            errors.append(f"Rank {row.get('rank')}: batch_id mismatch")
        if row.get("source_queue_sha256") != manifest.get("source_queue_sha256"):
            errors.append(f"Rank {row.get('rank')}: source_queue_sha256 mismatch")
        if not row.get("screened_at"):
            errors.append(f"Rank {row.get('rank')}: screened_at is blank")
        if not row.get("model"):
            errors.append(f"Rank {row.get('rank')}: model is blank")

    history_path = repo / "data/curated/screening/title_abstract_decision_history.csv"
    active_path = repo / "data/curated/screening/title_abstract_decisions.csv"
    relevance_path = repo / "data/curated/screening/title_abstract_relevance.csv"
    enriched_path = repo / "data/curated/screening/title_abstract_decisions_enriched.csv"
    queue_path = repo / manifest["source_queue"]
    status_path = repo / "docs/project/SCREENING_STATUS.md"
    history_fields, history = read_csv(history_path)
    if history_fields != CORE_FIELDS:
        errors.append("Existing history schema is invalid")
    existing_candidates = {row["candidate_id"] for row in history}
    for row in rows:
        if row["candidate_id"] in existing_candidates and not row.get("supersedes_screening_id"):
            errors.append(f"Candidate already has a decision and no supersession was declared: {row['candidate_id']}")
    combined = [*history, *rows]
    history_errors, _ = validate_history(combined)
    errors.extend(history_errors)

    # Validate the provenance target before modifying any curated state. This
    # prevents a duplicate batch ID or schema mismatch from failing after the
    # history and active snapshots have already been rewritten.
    batches_path = repo / "data/curated/screening/screening_batches.csv"
    batch_fields, batches = read_csv(batches_path)
    if batch_fields != BATCH_FIELDS:
        errors.append("screening_batches.csv schema mismatch")
    if any(batch.get("batch_id") == manifest.get("batch_id") for batch in batches):
        errors.append(f"Batch provenance already contains {manifest.get('batch_id')}")

    if errors:
        report = "VALIDATION FAILED\n" + "\n".join(f"- {error}" for error in errors) + "\n"
        (batch_dir / "validation_report.txt").write_text(report, encoding="utf-8")
        print(report)
        return 2

    # Canonical rewrite ensures valid quoting and stable column order.
    atomic_write_csv(output_path, CORE_FIELDS, rows)
    atomic_write_csv(history_path, CORE_FIELDS, combined)
    rebuild_errors = write_active_state(
        history_path=history_path,
        active_path=active_path,
        relevance_path=relevance_path,
        enriched_path=enriched_path,
        queue_path=queue_path,
        status_path=status_path,
    )
    if rebuild_errors:
        raise SystemExit("Active-state rebuild failed after validation: " + "; ".join(rebuild_errors))

    counts = Counter(row["decision"] for row in rows)
    manifest.update({
        "status": "finalized",
        "finalized_utc": now_utc(),
        "decision_count": len(rows),
        "included": counts["include"],
        "excluded": counts["exclude"],
        "unclear": counts["unclear"],
        "screened_rows_sha256": sha256_file(output_path),
        "history_sha256_after": sha256_file(history_path),
        "active_decisions_sha256_after": sha256_file(active_path),
        "quality_gates_passed": True,
    })
    write_json(manifest_path, manifest)
    (batch_dir / "validation_report.txt").write_text(
        f"VALIDATION PASSED\nBatch: {manifest['batch_id']}\nRows: {len(rows)}\n"
        f"Include: {counts['include']}\nExclude: {counts['exclude']}\nUnclear: {counts['unclear']}\n",
        encoding="utf-8",
    )
    (batch_dir / "batch_report.md").write_text(
        f"# Screening batch {manifest['batch_id']}\n\n"
        f"- Ranks: `{manifest['ranks']}`\n- Decisions: {len(rows)}\n"
        f"- Included: {counts['include']}\n- Excluded: {counts['exclude']}\n- Unclear: {counts['unclear']}\n"
        f"- Queue SHA-256: `{manifest['source_queue_sha256']}`\n- Status: finalized and validated\n",
        encoding="utf-8",
    )

    batches.append({
        "batch_id": manifest["batch_id"],
        "batch_type": manifest.get("batch_type", "title_abstract"),
        "ranks": manifest["ranks"],
        "protocol_version": manifest["protocol_version"],
        "screened_at": max(row["screened_at"] for row in rows),
        "input_queue_path": manifest["source_queue"],
        "input_queue_sha256": manifest["source_queue_sha256"],
        "screened_rows_path": str(output_path.relative_to(repo)).replace("\\", "/"),
        "screened_rows_sha256": manifest["screened_rows_sha256"],
        "decision_count": str(len(rows)),
        "included": str(counts["include"]),
        "excluded": str(counts["exclude"]),
        "unclear": str(counts["unclear"]),
        "provenance_status": "native_validated_batch",
        "quality_gates_passed": "true",
        "notes": "Finalized by scripts/research/finalize_screening_batch.py",
    })
    atomic_write_csv(batches_path, BATCH_FIELDS, batches)
    print(f"Finalized {manifest['batch_id']}: include={counts['include']} exclude={counts['exclude']} unclear={counts['unclear']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
