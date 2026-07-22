#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agri_cv_novelty.screening import (  # noqa: E402
    CORE_FIELDS,
    ENRICHED_FIELDS,
    WIDE_RELEVANCE_FIELDS,
    build_enriched_rows,
    compare_rows,
    read_csv,
    sha256_file,
    validate_against_queue,
    validate_history,
    write_active_state,
)


def paths(repo: Path) -> dict[str, Path]:
    return {
        "history": repo / "data/curated/screening/title_abstract_decision_history.csv",
        "active": repo / "data/curated/screening/title_abstract_decisions.csv",
        "relevance": repo / "data/curated/screening/title_abstract_relevance.csv",
        "enriched": repo / "data/curated/screening/title_abstract_decisions_enriched.csv",
        "batches": repo / "data/curated/screening/screening_batches.csv",
        "queue": repo / "outputs/screening_queue_2026-07-22/screening_queue.csv",
        "status": repo / "docs/project/SCREENING_STATUS.md",
    }


def validate(repo: Path) -> dict[str, object]:
    p = paths(repo)
    errors: list[str] = []
    warnings: list[str] = []
    for name, path in p.items():
        if name == "status":
            continue
        if not path.exists():
            errors.append(f"Missing required file: {path.relative_to(repo)}")
    if errors:
        return {"passed": False, "errors": errors, "warnings": warnings}

    history_fields, history = read_csv(p["history"])
    if history_fields != CORE_FIELDS:
        errors.append("History schema does not match the controlled screening schema")
    history_errors, expected_active = validate_history(history)
    errors.extend(history_errors)

    active_fields, active = read_csv(p["active"])
    if active_fields != CORE_FIELDS:
        errors.append("Active decision schema does not match the controlled screening schema")
    if expected_active:
        errors.extend(compare_rows(expected_active, active, CORE_FIELDS))

    relevance_fields, relevance = read_csv(p["relevance"])
    if relevance_fields != WIDE_RELEVANCE_FIELDS:
        errors.append("Relevance table schema does not match the controlled schema")
    if len(relevance) != len(active):
        errors.append(f"Relevance row count {len(relevance)} does not match active decision count {len(active)}")

    _, queue = read_csv(p["queue"])
    enriched_fields, enriched = read_csv(p["enriched"])
    if enriched_fields != ENRICHED_FIELDS:
        errors.append("Enriched decision view schema does not match the controlled schema")
    expected_enriched = build_enriched_rows(active, queue)
    errors.extend(compare_rows(expected_enriched, enriched, ENRICHED_FIELDS))
    queue_sha = sha256_file(p["queue"])
    errors.extend(validate_against_queue(active, queue, queue_sha256=queue_sha))

    _, batches = read_csv(p["batches"])
    seen_batch_ids: set[str] = set()
    for row in batches:
        batch_id = row.get("batch_id", "")
        if not batch_id:
            errors.append("Batch provenance row has blank batch_id")
            continue
        if batch_id in seen_batch_ids:
            errors.append(f"Duplicate batch_id: {batch_id}")
        seen_batch_ids.add(batch_id)
        rel = row.get("screened_rows_path", "")
        target = repo / rel
        if not target.exists():
            errors.append(f"Batch {batch_id}: missing screened_rows file {rel}")
            continue
        actual = sha256_file(target)
        expected = row.get("screened_rows_sha256", "").lower()
        if actual != expected:
            errors.append(f"Batch {batch_id}: screened_rows SHA-256 mismatch")

    if not p["status"].exists():
        warnings.append("SCREENING_STATUS.md is missing and should be regenerated")

    return {
        "passed": not errors,
        "history_events": len(history),
        "active_decisions": len(active),
        "queue_candidates": len(queue),
        "batch_records": len(batches),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or rebuild the normalized title/abstract screening state.")
    parser.add_argument("action", choices=["validate", "rebuild"])
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()

    if args.action == "rebuild":
        p = paths(repo)
        errors = write_active_state(
            history_path=p["history"],
            active_path=p["active"],
            relevance_path=p["relevance"],
            enriched_path=p["enriched"],
            queue_path=p["queue"],
            status_path=p["status"],
        )
        if errors:
            for error in errors:
                print(f"[ERROR] {error}")
            return 2

    result = validate(repo)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for warning in result["warnings"]:
        print(f"[WARN] {warning}")
    for error in result["errors"]:
        print(f"[ERROR] {error}")
    print(
        f"Screening state: passed={result['passed']} history={result.get('history_events', 0)} "
        f"active={result.get('active_decisions', 0)} queue={result.get('queue_candidates', 0)}"
    )
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
