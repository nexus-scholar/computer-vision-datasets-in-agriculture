#!/usr/bin/env python3
"""Fast, non-destructive consistency check for the research repository."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

REQUIRED = (
    "AGENTS.md",
    "opencode.json",
    "docs/workflow/WORKFLOW.md",
    "docs/workflow/QUALITY_GATES.md",
    "data/curated/templates/seed_resolution_audit.csv",
    "data/curated/templates/study_protocol_template.md",
    "scripts/research/build_accepted_graph.py",
    ".opencode/agents/research-lead.md",
    "tools/agri_cv_snowball_package/input/seed_papers_manifest.csv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check repository workflow structure and obvious consistency defects.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo.resolve()
    findings: list[tuple[str, str]] = []

    for rel in REQUIRED:
        if not (root / rel).exists():
            findings.append(("ERROR", f"Missing required workflow file: {rel}"))

    config_path = root / "opencode.json"
    if config_path.exists():
        try:
            json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(("ERROR", f"Invalid opencode.json: {exc}"))

    # Find exact duplicate tracked inputs outside generated/cache locations.
    candidates: list[Path] = []
    for base in (root / "data", root / "datasets-papers-2026-07-03", root / "tools"):
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.casefold() in {".csv", ".pdf", ".md", ".txt"}:
                    candidates.append(path)
    hashes: defaultdict[tuple[int, str], list[Path]] = defaultdict(list)
    for path in candidates:
        try:
            hashes[(path.stat().st_size, sha256(path))].append(path)
        except OSError:
            continue
    duplicate_groups = [paths for paths in hashes.values() if len(paths) > 1]
    for paths in duplicate_groups:
        rels = ", ".join(str(path.relative_to(root)) for path in paths)
        findings.append(("WARN", f"Exact duplicate files: {rels}"))

    try:
        result = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            findings.append(("WARN", "Git repository has no valid HEAD commit."))
    except OSError:
        findings.append(("INFO", "Git executable not available; Git baseline not checked."))

    for severity, message in findings:
        print(f"[{severity}] {message}")
    errors = sum(1 for severity, _ in findings if severity == "ERROR")
    warnings = sum(1 for severity, _ in findings if severity == "WARN")
    print(f"Summary: errors={errors}, warnings={warnings}, findings={len(findings)}")
    return 2 if errors else (1 if warnings else 0)


if __name__ == "__main__":
    raise SystemExit(main())
