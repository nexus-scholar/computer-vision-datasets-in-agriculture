from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

import requests
from lxml import etree

from . import __version__
from .config import Settings
from .http_client import PoliteSession
from .io_utils import append_csv, atomic_write_csv, now_utc, read_csv, redact_secrets, safe_segment, sha256_file, sha256_text, timestamp_id, write_json
from .models import Candidate, DownloadedArtifact, Work
from .queueing import work_from_queue_row
from .resolvers import auto_download_allowed, resolve_candidates
from .schema import ARTIFACT_REGISTRY_FIELDS, ATTEMPT_FIELDS, CANDIDATE_FIELDS, RESOLVER_ERROR_FIELDS


def acquire_queue(
    settings: Settings,
    queue_path: Path,
    artifact_set: str = "both",
    refresh: bool = False,
    allow_unknown_rights: bool = False,
    out_dir: Path | None = None,
) -> Path:
    _, queue_rows = read_csv(queue_path)
    works = [work_from_queue_row(row) for row in queue_rows]
    run_id = f"FTA_{timestamp_id()}"
    out_dir = out_dir or (settings.output_root / run_id)
    out_dir.mkdir(parents=True, exist_ok=False)

    session = PoliteSession(max_retries=settings.max_retries)
    session.headers.update({"User-Agent": settings.user_agent, "Accept": "*/*"})

    _, existing_rows = read_csv(settings.artifact_registry)
    recent_failures = _recent_failed_candidates(settings)
    existing: dict[tuple[str, str], dict[str, str]] = {}
    for row in existing_rows:
        if row.get("status") == "success" and (settings.repo / row.get("stored_path", "")).exists():
            existing[(row.get("paper_id", ""), row.get("artifact_type", ""))] = row

    candidate_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    resolver_errors: list[dict[str, str]] = []
    summary: list[dict[str, Any]] = []
    manual_rows: list[dict[str, Any]] = []

    for work in works:
        candidates, errors = resolve_candidates(settings, work, session)
        resolver_errors.extend(errors)
        candidate_rows.extend(_safe_candidate_row(candidate) for candidate in candidates)
        targets = _targets(artifact_set)
        paper_results: dict[str, str] = {}
        for target in targets:
            if not refresh and _has_target(existing, work.paper_id, target):
                paper_results[target] = "cached"
                continue
            selected = [candidate for candidate in candidates if _matches_target(candidate, target)]
            if not selected:
                paper_results[target] = "no_candidate"
                continue
            result = "failed"
            for candidate in selected:
                if not refresh and candidate.candidate_id in recent_failures:
                    attempt_rows.append(
                        _attempt_row(
                            run_id,
                            work,
                            candidate,
                            status="skipped_cooldown",
                            error=(
                                "A recent failed attempt exists for this exact candidate; "
                                "use --refresh to retry before the cooldown expires."
                            ),
                        )
                    )
                    result = "skipped_cooldown"
                    continue
                if not (auto_download_allowed(candidate, settings) or allow_unknown_rights):
                    attempt_rows.append(
                        _attempt_row(
                            run_id,
                            work,
                            candidate,
                            status="skipped_rights",
                            error="Rights status is unknown; use --allow-unknown-rights only for lawful local access.",
                        )
                    )
                    result = "skipped_rights"
                    continue
                started = now_utc()
                try:
                    artifact, response_meta = _download_candidate(settings, work, candidate, run_id, session)
                    completed = now_utc()
                    attempt_rows.append(
                        _attempt_row(
                            run_id,
                            work,
                            candidate,
                            status="success",
                            started_at=started,
                            completed_at=completed,
                            **response_meta,
                            artifact=artifact,
                        )
                    )
                    registry_row = _registry_row(work, candidate, artifact, run_id)
                    registry_rows.append(registry_row)
                    existing[(work.paper_id, artifact.artifact_type)] = registry_row
                    recent_failures.pop(candidate.candidate_id, None)
                    result = "success"
                    break
                except Exception as exc:
                    recent_failures[candidate.candidate_id] = now_utc()
                    attempt_rows.append(
                        _attempt_row(
                            run_id,
                            work,
                            candidate,
                            status="failed",
                            started_at=started,
                            completed_at=now_utc(),
                            error=redact_secrets(f"{type(exc).__name__}: {exc}", [settings.openalex_api_key, settings.semantic_scholar_api_key, settings.unpaywall_email]),
                        )
                    )
            paper_results[target] = result
        summary_row = {
            "paper_id": work.paper_id,
            "rank": work.rank,
            "title": work.title,
            "pdf_result": paper_results.get("pdf", "not_requested"),
            "structured_result": paper_results.get("structured", "not_requested"),
            "candidate_count": len(candidates),
            "resolver_error_count": len(errors),
        }
        summary.append(summary_row)
        unresolved_targets = [name for name, value in paper_results.items() if value not in {"success", "cached", "not_requested"}]
        if unresolved_targets:
            manual_rows.append({
                "paper_id": work.paper_id,
                "rank": work.rank,
                "title": work.title,
                "doi": work.doi,
                "arxiv_id": work.arxiv_id,
                "pmid": work.pmid,
                "pmcid": work.pmcid,
                "landing_url": work.landing_url,
                "unresolved_artifacts": ";".join(unresolved_targets),
                "reason": ";".join(f"{name}:{paper_results[name]}" for name in unresolved_targets),
                "recommended_action": "Check author/institutional repository or obtain a lawful local copy; import with an explicit rights status.",
            })

    atomic_write_csv(out_dir / "candidates.csv", CANDIDATE_FIELDS, candidate_rows)
    atomic_write_csv(out_dir / "attempts.csv", ATTEMPT_FIELDS, attempt_rows)
    _write_dynamic_csv(out_dir / "resolver_errors.csv", ["paper_id", "source", "error"], resolver_errors)
    _write_dynamic_csv(
        out_dir / "summary.csv",
        ["paper_id", "rank", "title", "pdf_result", "structured_result", "candidate_count", "resolver_error_count"],
        summary,
    )
    _write_dynamic_csv(
        out_dir / "manual_resolution_queue.csv",
        ["paper_id", "rank", "title", "doi", "arxiv_id", "pmid", "pmcid", "landing_url", "unresolved_artifacts", "reason", "recommended_action"],
        manual_rows,
    )
    if registry_rows:
        append_csv(settings.artifact_registry, ARTIFACT_REGISTRY_FIELDS, registry_rows)
    if attempt_rows:
        append_csv(settings.attempt_registry, ATTEMPT_FIELDS, attempt_rows)
    durable_resolver_errors = [
        {
            "error_id": "FTERR_" + sha256_text(
                f"{run_id}|{row.get('paper_id', '')}|{row.get('source', '')}|{row.get('error', '')}"
            )[:20],
            "run_id": run_id,
            "paper_id": row.get("paper_id", ""),
            "source": row.get("source", ""),
            "error": row.get("error", ""),
            "recorded_at": now_utc(),
        }
        for row in resolver_errors
    ]
    if durable_resolver_errors:
        append_csv(settings.resolver_error_registry, RESOLVER_ERROR_FIELDS, durable_resolver_errors)

    manifest = {
        "run_id": run_id,
        "tool_version": __version__,
        "created_at": now_utc(),
        "queue_path": str(queue_path.resolve()),
        "queue_sha256": sha256_file(queue_path),
        "artifact_set": artifact_set,
        "refresh": refresh,
        "allow_unknown_rights": allow_unknown_rights or settings.allow_unknown_rights,
        "work_count": len(works),
        "candidate_count": len(candidate_rows),
        "attempt_count": len(attempt_rows),
        "success_count": sum(1 for row in attempt_rows if row.get("status") == "success"),
        "sources": list(settings.source_order),
        "openalex_content_enabled": settings.openalex_content_enabled,
        "expected_openalex_content_cost_usd": round(
            sum(float(row.get("expected_cost_usd") or 0) for row in candidate_rows if row.get("source") == "openalex_content"), 2
        ),
    }
    write_json(out_dir / "run_manifest.json", manifest)
    _write_report(out_dir / "run_report.md", manifest, summary, resolver_errors)
    return out_dir


def import_local_artifact(
    settings: Settings,
    work: Work,
    source_path: Path,
    rights_status: str,
    license_value: str = "",
    version: str = "user_supplied",
    notes: str = "",
) -> dict[str, Any]:
    if rights_status not in {"open_license", "free_to_read_unknown_reuse", "local_research_only", "restricted"}:
        raise ValueError("Invalid rights status for manual import.")
    source_path = source_path.resolve()
    artifact_type, mime_type = _validate_file(source_path, expected_type=None, max_bytes=settings.max_bytes)
    digest = sha256_file(source_path)
    destination = settings.raw_dir / safe_segment(work.paper_id) / digest[:16] / f"source.{_extension(artifact_type)}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        _copy_atomic(source_path, destination)
    artifact_id = "FTA_" + sha256_text(f"{work.paper_id}|{digest}|manual")[:20]
    run_id = f"manual_{timestamp_id()}"
    row = {
        "artifact_id": artifact_id,
        "paper_id": work.paper_id,
        "rank": work.rank,
        "title": work.title,
        "source": "user_supplied",
        "artifact_type": artifact_type,
        "stored_path": str(destination.relative_to(settings.repo)).replace("\\", "/"),
        "sha256": digest,
        "size_bytes": source_path.stat().st_size,
        "mime_type": mime_type,
        "source_url": "",
        "final_url": "",
        "license": license_value,
        "version": version,
        "host_type": "local",
        "rights_status": rights_status,
        "acquired_at": now_utc(),
        "run_id": run_id,
        "candidate_id": "",
        "status": "success",
        "notes": notes,
    }
    append_csv(settings.artifact_registry, ARTIFACT_REGISTRY_FIELDS, [row])
    write_json(
        destination.parent / "source_manifest.json",
        {**row, "original_local_path": str(source_path), "redistribute": rights_status == "open_license"},
    )
    return row


def _download_candidate(
    settings: Settings,
    work: Work,
    candidate: Candidate,
    run_id: str,
    session: requests.Session,
) -> tuple[DownloadedArtifact, dict[str, Any]]:
    params = {"api_key": settings.openalex_api_key} if candidate.source == "openalex_content" else None
    last_error: Exception | None = None
    for attempt in range(1, settings.max_retries + 1):
        temp_path: Path | None = None
        try:
            with session.get(
                candidate.url,
                params=params,
                stream=True,
                timeout=settings.timeout_seconds,
                allow_redirects=True,
            ) as response:
                response.raise_for_status()
                content_length = int(response.headers.get("Content-Length") or 0)
                if content_length and content_length > settings.max_bytes:
                    raise ValueError(f"Content-Length {content_length} exceeds max {settings.max_bytes} bytes")
                suffix = ".pdf" if candidate.artifact_type == "pdf" else ".xml"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                    temp_path = Path(handle.name)
                    size = 0
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > settings.max_bytes:
                            raise ValueError(f"Download exceeds max {settings.max_bytes} bytes")
                        handle.write(chunk)
                actual_type, mime_type = _validate_file(temp_path, candidate.artifact_type, settings.max_bytes)
                digest = sha256_file(temp_path)
                destination = settings.raw_dir / safe_segment(work.paper_id) / digest[:16] / f"source.{_extension(actual_type)}"
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    os.replace(temp_path, destination)
                    temp_path = None
                stored_path = str(destination.relative_to(settings.repo)).replace("\\", "/")
                artifact = DownloadedArtifact(
                    paper_id=work.paper_id,
                    source=candidate.source,
                    artifact_type=actual_type,
                    source_url=_redact_url(candidate.url),
                    final_url=_redact_url(response.url),
                    stored_path=stored_path,
                    sha256=digest,
                    size_bytes=destination.stat().st_size,
                    mime_type=mime_type,
                    license=candidate.license,
                    version=candidate.version,
                    host_type=candidate.host_type,
                    rights_status=candidate.rights_status,
                    candidate_id=candidate.candidate_id,
                )
                write_json(
                    destination.parent / "source_manifest.json",
                    {
                        "paper_id": work.paper_id,
                        "rank": work.rank,
                        "title": work.title,
                        "source": candidate.source,
                        "candidate_id": candidate.candidate_id,
                        "source_url": artifact.source_url,
                        "final_url": artifact.final_url,
                        "artifact_type": actual_type,
                        "sha256": digest,
                        "size_bytes": artifact.size_bytes,
                        "mime_type": mime_type,
                        "license": candidate.license,
                        "version": candidate.version,
                        "rights_status": candidate.rights_status,
                        "acquired_at": now_utc(),
                        "run_id": run_id,
                        "metadata": candidate.metadata,
                    },
                )
                return artifact, {
                    "http_status": response.status_code,
                    "final_url": artifact.final_url,
                    "content_type": response.headers.get("Content-Type", ""),
                    "size_bytes": artifact.size_bytes,
                    "sha256": digest,
                    "stored_path": stored_path,
                }
        except Exception as exc:
            last_error = exc
            if attempt < settings.max_retries:
                time.sleep(min(2**attempt, 8))
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
    raise last_error or RuntimeError("Download failed")


def _validate_file(path: Path, expected_type: str | None, max_bytes: int) -> tuple[str, str]:
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("Artifact is empty")
    if size > max_bytes:
        raise ValueError(f"Artifact exceeds max {max_bytes} bytes")
    with path.open("rb") as handle:
        prefix = handle.read(16)
    if prefix.startswith(b"%PDF-"):
        if expected_type not in {None, "pdf"}:
            raise ValueError(f"Expected {expected_type}, received PDF")
        return "pdf", "application/pdf"
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as exc:
        raise ValueError("Artifact is neither a valid PDF nor well-formed XML") from exc
    root = etree.QName(tree.getroot()).localname.lower()
    if root == "tei":
        actual = "tei_xml"
    elif root in {"article", "articles", "pmc-articleset"}:
        actual = "jats_xml"
    elif root == "oai-pmh" and tree.xpath("//*[local-name()='article']"):
        actual = "jats_xml"
    else:
        actual = "xml"
    if expected_type == "pdf":
        raise ValueError(f"Expected PDF, received XML root {root}")
    if expected_type in {"jats_xml", "tei_xml"} and actual != expected_type:
        raise ValueError(f"Expected {expected_type}, received XML root {root}")
    return actual, "application/xml"


def _recent_failed_candidates(settings: Settings) -> dict[str, str]:
    """Return exact candidates whose latest durable audited outcome is a recent failure.

    The curated attempt registry is authoritative. Historical run-local attempts are
    also read as a compatibility fallback for repositories created before the
    durable registry was introduced. A later success clears an earlier failure.
    """

    if settings.failed_cooldown_hours <= 0:
        return {}
    latest: dict[str, tuple[datetime, str]] = {}

    def consume(rows: Iterable[dict[str, str]]) -> None:
        for row in rows:
            candidate_id = row.get("candidate_id", "").strip()
            completed = _parse_utc(row.get("completed_at", ""))
            if not candidate_id or completed is None:
                continue
            current = latest.get(candidate_id)
            if current is None or completed >= current[0]:
                latest[candidate_id] = (completed, row.get("status", ""))

    if settings.attempt_registry.exists():
        try:
            _, durable_rows = read_csv(settings.attempt_registry)
            consume(durable_rows)
        except Exception:
            pass

    if settings.output_root.exists():
        for attempts_path in settings.output_root.rglob("attempts.csv"):
            try:
                _, rows = read_csv(attempts_path)
            except Exception:
                continue
            consume(rows)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.failed_cooldown_hours)
    return {
        candidate_id: completed.isoformat().replace("+00:00", "Z")
        for candidate_id, (completed, status) in latest.items()
        if status == "failed" and completed >= cutoff
    }

def _parse_utc(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _registry_row(work: Work, candidate: Candidate, artifact: DownloadedArtifact, run_id: str) -> dict[str, Any]:
    return {
        "artifact_id": "FTA_" + sha256_text(f"{work.paper_id}|{artifact.sha256}|{candidate.source}")[:20],
        "paper_id": work.paper_id,
        "rank": work.rank,
        "title": work.title,
        "source": candidate.source,
        "artifact_type": artifact.artifact_type,
        "stored_path": artifact.stored_path,
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
        "mime_type": artifact.mime_type,
        "source_url": artifact.source_url,
        "final_url": artifact.final_url,
        "license": candidate.license,
        "version": candidate.version,
        "host_type": candidate.host_type,
        "rights_status": candidate.rights_status,
        "acquired_at": now_utc(),
        "run_id": run_id,
        "candidate_id": candidate.candidate_id,
        "status": "success",
        "notes": "",
    }


def _attempt_row(
    run_id: str,
    work: Work,
    candidate: Candidate,
    status: str,
    started_at: str | None = None,
    completed_at: str | None = None,
    error: str = "",
    artifact: DownloadedArtifact | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "attempt_id": "FTATT_" + sha256_text(f"{run_id}|{work.paper_id}|{candidate.candidate_id}|{started_at or now_utc()}")[:20],
        "run_id": run_id,
        "paper_id": work.paper_id,
        "candidate_id": candidate.candidate_id,
        "source": candidate.source,
        "artifact_type": artifact.artifact_type if artifact else candidate.artifact_type,
        "url": _redact_url(candidate.url),
        "started_at": started_at or now_utc(),
        "completed_at": completed_at or now_utc(),
        "status": status,
        "http_status": metadata.get("http_status", ""),
        "final_url": metadata.get("final_url", ""),
        "content_type": metadata.get("content_type", ""),
        "size_bytes": metadata.get("size_bytes", ""),
        "sha256": metadata.get("sha256", ""),
        "stored_path": metadata.get("stored_path", ""),
        "license": candidate.license,
        "version": candidate.version,
        "rights_status": candidate.rights_status,
        "error": error,
    }


def _safe_candidate_row(candidate: Candidate) -> dict[str, Any]:
    row = candidate.as_row()
    row["url"] = _redact_url(candidate.url)
    return row


def _targets(artifact_set: str) -> tuple[str, ...]:
    mapping = {"both": ("structured", "pdf"), "structured": ("structured",), "pdf": ("pdf",)}
    if artifact_set not in mapping:
        raise ValueError(f"Unknown artifact set: {artifact_set}")
    return mapping[artifact_set]


def _matches_target(candidate: Candidate, target: str) -> bool:
    return candidate.artifact_type == "pdf" if target == "pdf" else candidate.artifact_type in {"jats_xml", "tei_xml", "xml"}


def _has_target(existing: dict[tuple[str, str], dict[str, str]], paper_id: str, target: str) -> bool:
    if target == "pdf":
        return (paper_id, "pdf") in existing
    return any((paper_id, item) in existing for item in ("jats_xml", "tei_xml", "xml"))


def _extension(artifact_type: str) -> str:
    return "pdf" if artifact_type == "pdf" else "xml"


def _redact_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    safe_parts = []
    for item in parts.query.split("&"):
        key = item.split("=", 1)[0].lower()
        secret_keys = {
            "api_key", "apikey", "key", "email", "token", "access_token", "signature",
            "x-amz-signature", "x-amz-credential", "x-amz-security-token", "policy",
        }
        safe_parts.append(f"{key}=REDACTED" if key in secret_keys else item)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(safe_parts), parts.fragment))


def _copy_atomic(source: Path, destination: Path) -> None:
    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent, suffix=".tmp") as handle:
        temp = Path(handle.name)
        with source.open("rb") as input_handle:
            while chunk := input_handle.read(1024 * 1024):
                handle.write(chunk)
    os.replace(temp, destination)


def _write_dynamic_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    atomic_write_csv(path, fields, rows)


def _write_report(path: Path, manifest: dict[str, Any], summary: list[dict[str, Any]], errors: list[dict[str, str]]) -> None:
    lines = [
        "# Full-text acquisition run",
        "",
        f"- Run: `{manifest['run_id']}`",
        f"- Works: {manifest['work_count']}",
        f"- Candidates: {manifest['candidate_count']}",
        f"- Attempts: {manifest['attempt_count']}",
        f"- Successful artifacts: {manifest['success_count']}",
        f"- Resolver errors: {len(errors)}",
        "",
        "## Per-paper outcomes",
        "",
        "| Rank | Paper | Structured | PDF | Candidates |",
        "|---:|---|---|---|---:|",
    ]
    for row in summary:
        title = str(row["title"]).replace("|", "\\|")
        lines.append(
            f"| {row['rank']} | {title} | {row['structured_result']} | {row['pdf_result']} | {row['candidate_count']} |"
        )
    if errors:
        lines.extend(["", "## Resolver warnings", ""])
        for error in errors[:100]:
            lines.append(f"- `{error['paper_id']}` / `{error['source']}`: {error['error']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
