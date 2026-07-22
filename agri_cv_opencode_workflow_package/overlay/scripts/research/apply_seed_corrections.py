#!/usr/bin/env python3
"""Preview or apply controlled corrections to a seed manifest."""
from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or apply seed-manifest corrections by row_id.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Write corrected manifest here instead of in place")
    parser.add_argument("--apply", action="store_true", help="Actually write changes; default is preview only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_fields, manifest_rows = read_csv(args.manifest)
    correction_fields, correction_rows = read_csv(args.corrections)
    if "row_id" not in manifest_fields or "row_id" not in correction_fields:
        raise SystemExit("Both CSVs must contain row_id.")

    by_id = {row.get("row_id", ""): row for row in manifest_rows}
    changes: list[tuple[str, str, str, str]] = []
    missing_ids: list[str] = []
    for correction in correction_rows:
        row_id = correction.get("row_id", "").strip()
        target = by_id.get(row_id)
        if target is None:
            missing_ids.append(row_id)
            continue
        for field, new_value in correction.items():
            if field == "row_id" or not (new_value or "").strip():
                continue
            if field not in manifest_fields:
                manifest_fields.append(field)
                for row in manifest_rows:
                    row.setdefault(field, "")
            old_value = target.get(field, "")
            if old_value != new_value:
                changes.append((row_id, field, old_value, new_value))
                target[field] = new_value

    print(f"Manifest: {args.manifest}")
    print(f"Corrections: {args.corrections}")
    print(f"Rows changed: {len({change[0] for change in changes})}; field changes: {len(changes)}")
    for row_id, field, old, new in changes:
        print(f"  {row_id}.{field}: {old!r} -> {new!r}")
    if missing_ids:
        print(f"Missing row IDs in manifest: {', '.join(missing_ids)}")

    if not args.apply:
        print("Preview only. Re-run with --apply to write changes.")
        return 1 if missing_ids else 0

    destination = args.output or args.manifest
    if destination.resolve() == args.manifest.resolve():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = args.manifest.with_name(args.manifest.name + f".bak-{stamp}")
        shutil.copy2(args.manifest, backup)
        print(f"Backup: {backup}")
    write_csv(destination, manifest_fields, manifest_rows)
    print(f"Wrote corrected manifest: {destination}")
    return 1 if missing_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
