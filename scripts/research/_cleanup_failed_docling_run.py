"""Deterministic correction event: remove extraction-registry rows created by a
docling-run that failed for the wrong reason (venv Scripts dir not on PATH, so
the `docling` executable was not found -- WinError 2).

Only rows with run_id == FTP_20260807T172443Z and qa_status == 'fail' are
removed. The three manual_review rows from that run (publisher XML extraction)
are retained because they are valid.

Reprocessing those papers with a correct PATH is expected to supersede nothing
here, because the fail rows no longer exist.
"""

from pathlib import Path
from typing import Any

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import atomic_write_csv, read_csv
from agri_fulltext.schema import EXTRACTION_REGISTRY_FIELDS

BAD_RUN_ID = "FTP_20260807T172443Z"
BAD_QA = "fail"


def main() -> None:
    settings = load_settings(Path(__file__).resolve().parents[2])
    registry_path = settings.extraction_registry
    _, rows = read_csv(registry_path)

    dropped = [r for r in rows if r.get("run_id") == BAD_RUN_ID and r.get("qa_status") == BAD_QA]
    kept_fail = [r for r in rows if r.get("run_id") == BAD_RUN_ID and r.get("qa_status") != BAD_QA]
    kept = [r for r in rows if r.get("run_id") != BAD_RUN_ID]

    print(f"rows read: {len(rows)}")
    print(f"rows dropped (run_id={BAD_RUN_ID}, qa_status={BAD_QA}): {len(dropped)}")
    print(f"rows retained from same run: {len(kept_fail)}")
    print(f"rows kept total: {len(kept) + len(kept_fail)}")

    if not dropped:
        print("nothing to drop; aborting without write")
        return

    atomic_write_csv(registry_path, EXTRACTION_REGISTRY_FIELDS, kept + kept_fail)
    print("wrote corrected registry: ", registry_path)


if __name__ == "__main__":
    main()
