#!/usr/bin/env python3
"""Install the OpenCode research workflow overlay non-destructively."""
from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_tree(source: Path, destination: Path, backup_root: Path, force: bool) -> tuple[int, int, int]:
    copied = identical = conflicts = 0
    for src in sorted(path for path in source.rglob("*") if path.is_file()):
        rel = src.relative_to(source)
        if any(part in {"__pycache__", ".pytest_cache"} for part in rel.parts) or src.suffix in {".pyc", ".pyo"}:
            continue
        dst = destination / rel
        if dst.exists():
            if sha256(src) == sha256(dst):
                identical += 1
                continue
            if not force:
                print(f"CONFLICT (not overwritten): {rel}")
                conflicts += 1
                continue
            backup = backup_root / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"COPIED: {rel}")
        copied += 1
    return copied, identical, conflicts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the agricultural CV OpenCode workflow overlay.")
    parser.add_argument("--repo", type=Path, required=True, help="Target repository root")
    parser.add_argument("--force", action="store_true", help="Back up and overwrite conflicting destination files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_root = Path(__file__).resolve().parent
    repo = args.repo.resolve()
    if not (repo / "pyproject.toml").exists():
        raise SystemExit(f"Target does not look like the expected repository: {repo}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = repo / ".workflow-backup" / stamp
    copied, identical, conflicts = copy_tree(package_root / "overlay", repo, backup_root, args.force)

    config_source = package_root / "config" / "seed_corrections.csv"
    config_dest = repo / "config" / "seed_corrections.csv"
    config_dest.parent.mkdir(parents=True, exist_ok=True)
    if config_dest.exists() and sha256(config_source) != sha256(config_dest):
        if args.force:
            backup = backup_root / "config" / "seed_corrections.csv"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config_dest, backup)
            shutil.copy2(config_source, config_dest)
            copied += 1
        else:
            print("CONFLICT (not overwritten): config/seed_corrections.csv")
            conflicts += 1
    elif not config_dest.exists():
        shutil.copy2(config_source, config_dest)
        print("COPIED: config/seed_corrections.csv")
        copied += 1
    else:
        identical += 1

    print(f"\nInstall summary: copied={copied}, identical={identical}, conflicts={conflicts}")
    if args.force and backup_root.exists():
        print(f"Backups: {backup_root}")
    if conflicts:
        print("Re-run with --force only after reviewing conflicts. Existing files were preserved.")
        return 1
    print("Next: review README_INSTALL.md, preview both patches with git apply --check, then run /status in OpenCode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
