#!/usr/bin/env python3
"""Phase 2c: merge batch tagging results into the structured matrix.
Also deduplicates by paper_id and produces gap summary statistics."""

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools/fulltext_pipeline" / "src"))
from agri_fulltext.io_utils import read_csv, atomic_write_csv


GAP_DIMENSIONS = [
    ("split_level", ("random", "unclear")),
    ("baseline_strength", ("sota_only", "unclear", "none")),
    ("calibration_reported", ("no", "partial")),
    ("cross_sensor_test", ("same_sensor", "unclear")),
    ("code_available", ("not_available", "unclear")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--batch-csvs", nargs="+",
                    help="Tagged batch result CSV paths. Default: reads outputs/mga_batch_*.csv")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    _, matrix = read_csv(repo / "outputs" / "method_gap_matrix.csv")

    # Load batch results
    if args.batch_csvs:
        batch_files = [Path(f) for f in args.batch_csvs]
    else:
        batch_files = sorted(repo.glob("outputs/mga_batch_*_results.csv"))

    results = {}
    for bf in batch_files:
        if not bf.exists():
            print(f"WARNING: {bf} not found, skipping")
            continue
        _, rows = read_csv(bf)
        for r in rows:
            pid = r.get("paper_id", "")
            results[pid] = r
        print(f"Loaded {len(rows)} tags from {bf}")

    # Merge into matrix, deduplicating by paper_id
    seen = set()
    merged = []
    for row in matrix:
        pid = row["paper_id"]
        if pid in seen:
            continue
        seen.add(pid)

        tag = results.get(pid, {})
        row["split_level"] = tag.get("split_level", "")
        row["baseline_strength"] = tag.get("baseline_strength", "")
        row["calibration_reported"] = tag.get("calibration_reported", "")
        row["cross_sensor_test"] = tag.get("cross_sensor_test", "")
        row["code_available"] = tag.get("code_available", "")
        row["dataset_role"] = tag.get("dataset_role", "")
        row["confidence_notes"] = tag.get("confidence_notes", "")
        merged.append(row)

    fields = list(merged[0].keys())
    out_path = repo / "outputs" / "method_gap_matrix.csv"
    atomic_write_csv(out_path, fields, merged)
    print(f"\nFinal matrix: {len(merged)} rows -> {out_path}")

    # Validate
    empty_cells = 0
    for col in ["split_level", "baseline_strength", "calibration_reported",
                 "cross_sensor_test", "code_available", "dataset_role"]:
        empty = sum(1 for r in merged if not r.get(col, ""))
        if empty:
            print(f"WARNING: {col} has {empty} empty cells")
            empty_cells += empty
    if empty_cells == 0:
        print("All 6 tag columns: 0 empty cells (OK)")

    # Summary
    print("\n=== METHOD-GAP SUMMARY ===")
    for dim, label in [
        ("split_level", "Split Level"),
        ("baseline_strength", "Baseline Strength"),
        ("calibration_reported", "Calibration"),
        ("cross_sensor_test", "Cross-Sensor"),
        ("code_available", "Code Available"),
        ("dataset_role", "Dataset Role"),
    ]:
        vals = [r.get(dim, "") for r in merged if r.get(dim, "")]
        c = Counter(vals)
        total = len(vals)
        print(f"\n{label}:")
        for tag, count in sorted(c.items(), key=lambda x: -x[1]):
            print(f"  {tag:25s} {count:3d}/{total} ({count / total * 100:5.1f}%)")

    gap_counts = Counter()
    for r in merged:
        gaps = sum(
            1 for dim, risky_tags in GAP_DIMENSIONS if r.get(dim, "") in risky_tags
        )
        gap_counts[gaps] += 1

    print(f"\n=== GAP COUNTS ===")
    for gaps in sorted(gap_counts.keys()):
        count = gap_counts[gaps]
        print(f"  {gaps} gap(s): {count:2d}/{len(merged)} ({count / len(merged) * 100:5.1f}%)")

    multi = sum(c for g, c in gap_counts.items() if g >= 4)
    print(f"\nPapers with >=4 gaps: {multi}/{len(merged)} ({multi / len(merged) * 100:.0f}%)")

    print("\nPhase 2 complete.")


if __name__ == "__main__":
    main()
