from datetime import datetime, timezone
from pathlib import Path

from agri_fulltext.acquisition import _recent_failed_candidates
from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import atomic_write_csv
from agri_fulltext.schema import ATTEMPT_FIELDS


def _row(candidate_id: str, status: str, completed_at: str):
    return {
        "attempt_id": f"a-{candidate_id}-{status}",
        "run_id": "r",
        "paper_id": "p",
        "candidate_id": candidate_id,
        "source": "test",
        "artifact_type": "pdf",
        "url": "https://example.org/a.pdf",
        "started_at": completed_at,
        "completed_at": completed_at,
        "status": status,
        "http_status": "",
        "final_url": "",
        "content_type": "",
        "size_bytes": "",
        "sha256": "",
        "stored_path": "",
        "license": "",
        "version": "",
        "rights_status": "open_license",
        "error": "",
    }


def test_recent_failure_cooldown_uses_latest_outcome(tmp_path: Path):
    repo = tmp_path / "repo"
    settings = load_settings(repo)
    first = settings.output_root / "FTA_1/attempts.csv"
    first.parent.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    atomic_write_csv(first, ATTEMPT_FIELDS, [_row("c1", "failed", now), _row("c2", "failed", now)])
    second = settings.output_root / "FTA_2/attempts.csv"
    second.parent.mkdir(parents=True)
    atomic_write_csv(second, ATTEMPT_FIELDS, [_row("c2", "success", now)])
    result = _recent_failed_candidates(settings)
    assert "c1" in result
    assert "c2" not in result


def test_recent_failure_cooldown_survives_run_folder_cleanup(tmp_path: Path):
    repo = tmp_path / "repo"
    settings = load_settings(repo)
    settings.attempt_registry.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    atomic_write_csv(
        settings.attempt_registry,
        ATTEMPT_FIELDS,
        [_row("durable-candidate", "failed", now)],
    )
    result = _recent_failed_candidates(settings)
    assert "durable-candidate" in result
