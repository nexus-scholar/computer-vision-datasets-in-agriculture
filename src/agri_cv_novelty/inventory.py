from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_MARKERS = ("pyproject.toml", "PROJECT_INDEX.md")


@dataclass(frozen=True)
class CsvSummary:
    path: Path
    rows: int
    columns: tuple[str, ...]


@dataclass(frozen=True)
class FileRecord:
    path: Path
    size_bytes: int
    sha256: str


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if all((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    raise RuntimeError(f"Could not find project root from {current}")


def summarize_csv(path: Path) -> CsvSummary:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = sum(1 for _ in reader)
        columns = tuple(reader.fieldnames or ())
    return CsvSummary(path=path, rows=rows, columns=columns)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from sorted(child for child in path.rglob("*") if child.is_file())


def build_manifest(root: Path, paths: Iterable[Path]) -> list[FileRecord]:
    records: list[FileRecord] = []
    for path in iter_files(paths):
        records.append(
            FileRecord(
                path=path.relative_to(root),
                size_bytes=path.stat().st_size,
                sha256=sha256_file(path),
            )
        )
    return records


def write_manifest(path: Path, records: Iterable[FileRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "path": record.path.as_posix(),
                    "size_bytes": record.size_bytes,
                    "sha256": record.sha256,
                }
            )


def print_csv_group(title: str, summaries: Iterable[CsvSummary], root: Path) -> None:
    print(title)
    for summary in summaries:
        columns_preview = ", ".join(summary.columns[:4])
        if len(summary.columns) > 4:
            columns_preview += ", ..."
        print(f"  - {summary.path.relative_to(root)}: {summary.rows} rows ({columns_preview})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect local research inputs.")
    parser.add_argument(
        "--write-manifest",
        type=Path,
        help="Write a CSV manifest with size and SHA-256 for reference files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = find_project_root()

    citation_dir = root / "data" / "raw" / "citation_exports"
    snowball_input_dir = root / "tools" / "agri_cv_snowball_package" / "input"
    papers_dir = root / "datasets-papers-2026-07-03"
    references_dir = root / "references"

    citation_summaries = [summarize_csv(path) for path in sorted(citation_dir.glob("*.csv"))]
    snowball_summaries = [summarize_csv(path) for path in sorted(snowball_input_dir.glob("*.csv"))]
    pdfs = sorted(papers_dir.glob("*.pdf"))

    print(f"Project root: {root}")
    print_csv_group("Citation exports", citation_summaries, root)
    print_csv_group("Snowball seed inputs", snowball_summaries, root)
    print(f"Local PDFs: {len(pdfs)} files in {papers_dir.relative_to(root)}")

    manifest_paths = [references_dir, citation_dir, snowball_input_dir, papers_dir]
    records = build_manifest(root, manifest_paths)
    print(f"Manifest scope: {len(records)} files")

    if args.write_manifest:
        output_path = args.write_manifest
        if not output_path.is_absolute():
            output_path = root / output_path
        write_manifest(output_path, records)
        try:
            display_path = output_path.relative_to(root)
        except ValueError:
            display_path = output_path
        print(f"Wrote manifest: {display_path}")


if __name__ == "__main__":
    main()

