from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_segment(value: str, max_length: int = 96) -> str:
    value = value.strip().replace("https://", "").replace("http://", "")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    if not value:
        value = "paper"
    if len(value) > max_length:
        suffix = sha256_text(value)[:10]
        value = f"{value[: max_length - 11]}_{suffix}"
    return value


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def atomic_write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", delete=False, dir=path.parent, suffix=".tmp"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_cell(row.get(key, "")) for key in fieldnames})
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def append_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    existing_fields, existing_rows = read_csv(path)
    if existing_fields and list(existing_fields) != list(fieldnames):
        raise ValueError(f"Schema mismatch for {path}: {existing_fields} != {list(fieldnames)}")
    atomic_write_csv(path, fieldnames, [*existing_rows, *rows])


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_rank_spec(value: str | None) -> set[int] | None:
    if value is None or not value.strip():
        return None
    result: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if re.fullmatch(r"\d+", part):
            result.add(int(part))
            continue
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if not match:
            raise ValueError(f"Invalid rank specification: {part!r}")
        start, end = map(int, match.groups())
        if end < start:
            raise ValueError(f"Rank range ends before it starts: {part!r}")
        result.update(range(start, end + 1))
    return result

_SECRET_QUERY_RE = re.compile(r"([?&](?:api_key|apikey|key|email|token|access_token|signature|x-amz-signature|x-amz-credential|x-amz-security-token|policy)=)[^&\s]+", re.IGNORECASE)


def redact_secrets(value: str, explicit_values: Sequence[str] = ()) -> str:
    result = _SECRET_QUERY_RE.sub(r"\1REDACTED", value or "")
    for secret in explicit_values:
        if secret:
            result = result.replace(secret, "REDACTED")
    return result
