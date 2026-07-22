#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agri_cv_novelty.screening import CORE_FIELDS, atomic_write_csv, now_utc, read_csv, sha256_file, write_json  # noqa: E402

INPUT_FIELDS = [
    "rank", "candidate_id", "title", "year", "authors", "venue", "doi", "arxiv_id", "pmid", "pmcid",
    "providers", "provider_ids", "seed_ids", "dataset_names", "directions", "is_open_access", "landing_url",
    "pdf_url", "abstract",
]


def parse_rank_spec(value: str) -> list[int]:
    value = value.strip()
    if re.fullmatch(r"\d+", value):
        return [int(value)]
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", value)
    if not match:
        raise ValueError("Rank specification must be N or N-M")
    start, end = map(int, match.groups())
    if end < start:
        raise ValueError("Rank range end must not be below start")
    return list(range(start, end + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare one bounded title/abstract screening batch.")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--ranks", help="Rank N or range N-M; default is next 10 unscreened ranks")
    parser.add_argument("--max-batch", type=int, default=20)
    args = parser.parse_args()
    repo = args.repo.resolve()
    queue_path = repo / "outputs/screening_queue_2026-07-22/screening_queue.csv"
    active_path = repo / "data/curated/screening/title_abstract_decisions.csv"
    batches_path = repo / "data/curated/screening/screening_batches.csv"
    _, queue = read_csv(queue_path)
    _, active = read_csv(active_path)
    screened_ranks = {int(row["rank"]) for row in active}

    if args.ranks:
        ranks = parse_rank_spec(args.ranks)
    else:
        ranks = [int(row["screening_rank"]) for row in queue if int(row["screening_rank"]) not in screened_ranks][:10]
    if not ranks:
        raise SystemExit("No unscreened ranks remain.")
    if len(ranks) > args.max_batch:
        raise SystemExit(f"Batch size {len(ranks)} exceeds maximum {args.max_batch}.")
    overlap = sorted(set(ranks) & screened_ranks)
    if overlap:
        raise SystemExit(f"Requested ranks are already screened: {overlap}")

    by_rank = {int(row["screening_rank"]): row for row in queue}
    missing = [rank for rank in ranks if rank not in by_rank]
    if missing:
        raise SystemExit(f"Ranks do not exist in the frozen queue: {missing}")

    _, batches = read_csv(batches_path)
    numeric = [int(m.group(1)) for row in batches if (m := re.fullmatch(r"B(\d+)", row.get("batch_id", "")))]
    batch_number = max(numeric, default=0) + 1
    batch_id = f"B{batch_number:03d}"
    start, end = min(ranks), max(ranks)
    batch_dir = repo / "outputs/screening_batches" / f"batch_{batch_number:03d}_ranks_{start}-{end}"
    if batch_dir.exists():
        raise SystemExit(f"Refusing to overwrite existing batch directory: {batch_dir}")
    batch_dir.mkdir(parents=True)

    input_rows = []
    templates = []
    queue_sha = sha256_file(queue_path)
    for rank in ranks:
        row = by_rank[rank]
        input_rows.append({
            "rank": rank,
            "candidate_id": row.get("canonical_paper_id", ""),
            "title": row.get("title", ""),
            "year": row.get("year", ""),
            "authors": row.get("authors", ""),
            "venue": row.get("venue", ""),
            "doi": row.get("doi", ""),
            "arxiv_id": row.get("arxiv_id", ""),
            "pmid": row.get("pmid", ""),
            "pmcid": row.get("pmcid", ""),
            "providers": row.get("providers", ""),
            "provider_ids": row.get("provider_ids", ""),
            "seed_ids": row.get("seed_ids", ""),
            "dataset_names": row.get("dataset_names", ""),
            "directions": row.get("directions", ""),
            "is_open_access": row.get("is_open_access", ""),
            "landing_url": row.get("landing_url", ""),
            "pdf_url": row.get("pdf_url", ""),
            "abstract": row.get("abstract", ""),
        })
        template = {field: "" for field in CORE_FIELDS}
        template.update({
            "screening_id": f"TA_R{rank:04d}",
            "candidate_id": row.get("canonical_paper_id", ""),
            "rank": str(rank),
            "title": row.get("title", ""),
            "abstract_available": "yes" if row.get("abstract", "").strip() else "no",
            "full_text_available": "unknown",
            "identity_status": "confirmed",
            "reviewer": "opencode_ai",
            "protocol_version": "AI_SCREENING_V1",
            "batch_id": batch_id,
            "source_queue_sha256": queue_sha,
        })
        templates.append(template)

    input_path = batch_dir / "input_rows.csv"
    template_path = batch_dir / "screened_rows_template.csv"
    atomic_write_csv(input_path, INPUT_FIELDS, input_rows)
    atomic_write_csv(template_path, CORE_FIELDS, templates)
    manifest = {
        "batch_id": batch_id,
        "batch_type": "title_abstract",
        "ranks": f"{start}-{end}" if start != end else str(start),
        "requested_ranks": ranks,
        "created_utc": now_utc(),
        "status": "prepared",
        "protocol_version": "AI_SCREENING_V1",
        "source_queue": str(queue_path.relative_to(repo)).replace("\\", "/"),
        "source_queue_sha256": queue_sha,
        "active_decisions_sha256_before": sha256_file(active_path),
        "input_rows_sha256": sha256_file(input_path),
        "template_sha256": sha256_file(template_path),
        "expected_output": str((batch_dir / "screened_rows.csv").relative_to(repo)).replace("\\", "/"),
    }
    write_json(batch_dir / "batch_manifest.json", manifest)
    print(f"Prepared {batch_id}: {batch_dir.relative_to(repo)}")
    print(f"Fill: {(batch_dir / 'screened_rows.csv').relative_to(repo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
