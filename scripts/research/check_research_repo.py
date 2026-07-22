#!/usr/bin/env python3
"""Fast, non-destructive repository and research-state consistency check."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agri_cv_novelty.screening import read_csv  # noqa: E402

REQUIRED = (
    "AGENTS.md",
    "opencode.json",
    "config/screening_protocol_v1.md",
    "docs/project/CURRENT_STATE.md",
    "docs/project/SCREENING_STATUS.md",
    "docs/workflow/WORKFLOW.md",
    "docs/workflow/QUALITY_GATES.md",
    "data/raw/seed_papers/manifest.csv",
    "data/raw/migration_archives/pre_cleanup_screening_state_2026-07-22.manifest.json",
    "data/curated/screening/title_abstract_decision_history.csv",
    "data/curated/screening/title_abstract_decisions.csv",
    "data/curated/screening/title_abstract_relevance.csv",
    "data/curated/screening/title_abstract_decisions_enriched.csv",
    "data/curated/screening/screening_batches.csv",
    "scripts/research/screening_state.py",
    "scripts/research/prepare_screening_batch.py",
    "scripts/research/finalize_screening_batch.py",
    ".opencode/commands/screen-paper.md",
    "tools/agri_cv_snowball_package/input/seed_papers_manifest.csv",
)

REMOVED_PATHS = (
    ".agents",
    ".codex",
    "agri_cv_opencode_workflow_package",
    "datasets-papers-2026-07-03",
    "tools/agri_cv_snowball_package/input/seed_papers_original.csv",
    "tools/agri_cv_snowball_package/input/seed_papers_manifest.csv.bak-20260722T142718Z",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check workflow structure, hashes, curated CSVs, and screening state.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo.resolve()
    findings: list[tuple[str, str]] = []

    for rel in REQUIRED:
        if not (root / rel).exists():
            findings.append(("ERROR", f"Missing required file: {rel}"))
    for rel in REMOVED_PATHS:
        if (root / rel).exists():
            findings.append(("WARN", f"Stale path should be removed: {rel}"))

    config_path = root / "opencode.json"
    if config_path.exists():
        try:
            json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(("ERROR", f"Invalid opencode.json: {exc}"))

    # All curated CSVs must parse without excess columns.
    curated = root / "data/curated"
    if curated.exists():
        for path in curated.rglob("*.csv"):
            try:
                read_csv(path)
            except (OSError, ValueError, csv.Error) as exc:
                findings.append(("ERROR", f"Malformed curated CSV {path.relative_to(root)}: {exc}"))

    # Verify local seed PDFs against their immutable manifest.
    paper_manifest = root / "data/raw/seed_papers/manifest.csv"
    if paper_manifest.exists():
        try:
            _, rows = read_csv(paper_manifest)
            if len(rows) != 13:
                findings.append(("ERROR", f"Seed-paper manifest has {len(rows)} rows; expected 13"))
            for row in rows:
                path = root / row.get("local_path", "")
                if not path.exists():
                    findings.append(("ERROR", f"Missing seed PDF: {row.get('local_path')}"))
                elif sha256(path) != row.get("sha256", "").lower():
                    findings.append(("ERROR", f"Seed PDF hash mismatch: {row.get('local_path')}"))
        except (OSError, ValueError, csv.Error) as exc:
            findings.append(("ERROR", f"Could not validate seed-paper manifest: {exc}"))

    # Verify the compressed provider cache archive.
    archive_manifest = root / "data/raw/api_archives/snowball_api_caches_2026-07-22.manifest.json"
    archive_path = root / "data/raw/api_archives/snowball_api_caches_2026-07-22.zip"
    if archive_manifest.exists() and archive_path.exists():
        try:
            manifest = json.loads(archive_manifest.read_text(encoding="utf-8"))
            if sha256(archive_path) != manifest.get("archive_sha256"):
                findings.append(("ERROR", "Historical API cache archive hash mismatch"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(("ERROR", f"Could not validate API cache archive: {exc}"))

    # Verify the exact pre-cleanup screening archive retained for audit.
    migration_manifest = root / "data/raw/migration_archives/pre_cleanup_screening_state_2026-07-22.manifest.json"
    migration_archive = root / "data/raw/migration_archives/pre_cleanup_screening_state_2026-07-22.zip"
    if migration_manifest.exists() and migration_archive.exists():
        try:
            manifest = json.loads(migration_manifest.read_text(encoding="utf-8"))
            if sha256(migration_archive) != manifest.get("archive_sha256"):
                findings.append(("ERROR", "Pre-cleanup screening archive hash mismatch"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(("ERROR", f"Could not validate pre-cleanup screening archive: {exc}"))

    # Active run directories should no longer contain hundreds of live cache files.
    live_caches = list((root / "outputs").glob("snowball_*/cache")) if (root / "outputs").exists() else []
    if live_caches:
        findings.append(("WARN", f"Live provider cache directories remain: {', '.join(str(p.relative_to(root)) for p in live_caches)}"))

    transient_paths = [
        *root.rglob("__pycache__"),
        *root.rglob("*.pyc"),
        root / ".pytest_cache",
    ]
    transient_paths = [path for path in transient_paths if path.exists()]
    if transient_paths:
        findings.append(("INFO", f"Ignored transient Python/test artifacts present: {len(transient_paths)} paths"))

    # Detect exact duplicate active source files; exclude generated output and immutable archives.
    candidates: list[Path] = []
    for base in (root / "data", root / "tools", root / "config"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in {".csv", ".pdf", ".md", ".txt"}:
                continue
            if "api_archives" in path.parts:
                continue
            candidates.append(path)
    hashes: defaultdict[tuple[int, str], list[Path]] = defaultdict(list)
    for path in candidates:
        try:
            hashes[(path.stat().st_size, sha256(path))].append(path)
        except OSError:
            continue
    for paths in hashes.values():
        if len(paths) > 1:
            rels = ", ".join(str(path.relative_to(root)) for path in paths)
            findings.append(("WARN", f"Exact duplicate active files: {rels}"))

    # Delegate the normalized screening-state check.
    screening_script = root / "scripts/research/screening_state.py"
    if screening_script.exists():
        result = subprocess.run(
            [sys.executable, str(screening_script), "validate", "--repo", str(root)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).strip().replace("\n", " | ")
            findings.append(("ERROR", f"Screening-state validation failed: {detail}"))

    # Only evaluate Git when the uploaded/working tree actually includes .git.
    if (root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                findings.append(("WARN", "Git repository has no valid HEAD commit"))
        except OSError:
            findings.append(("INFO", "Git executable not available; Git baseline not checked"))

    for severity, message in findings:
        print(f"[{severity}] {message}")
    errors = sum(1 for severity, _ in findings if severity == "ERROR")
    warnings = sum(1 for severity, _ in findings if severity == "WARN")
    print(f"Summary: errors={errors}, warnings={warnings}, findings={len(findings)}")
    return 2 if errors else (1 if warnings else 0)


if __name__ == "__main__":
    raise SystemExit(main())
