from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .config import Settings
from .io_utils import append_csv, atomic_write_csv, boolish, now_utc, parse_rank_spec, read_csv, sha256_file, timestamp_id, write_json
from .models import Work
from .schema import ACQUISITION_BATCH_FIELDS, FULLTEXT_QUEUE_FIELDS, SELECTION_FIELDS


class QueueValidationError(Exception):
    pass


def _repo_rel(settings: Settings, path: Path) -> str:
    try:
        return str(path.relative_to(settings.repo)).replace("\\", "/")
    except ValueError:
        return str(path)


def parse_provider_ids(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in (value or "").split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        key, item = part.split(":", 1)
        result[key.strip().lower()] = item.strip()
    return result


def load_eligible_works(
    settings: Settings,
    decisions: Iterable[str] = ("include", "unclear"),
    rank_spec: str | None = None,
) -> list[Work]:
    wanted_decisions = {item.strip().lower() for item in decisions}
    wanted_ranks = parse_rank_spec(rank_spec)
    _, decision_rows = read_csv(settings.decisions_path)
    _, queue_rows = read_csv(settings.queue_path)
    queue_by_id = {row.get("canonical_paper_id", ""): row for row in queue_rows}
    queue_by_rank = {row.get("screening_rank", ""): row for row in queue_rows}

    works: list[Work] = []
    for decision in decision_rows:
        decision_value = decision.get("decision", "").strip().lower()
        if decision_value not in wanted_decisions:
            continue
        rank = int(decision.get("rank") or 0)
        if rank <= 0 or (wanted_ranks is not None and rank not in wanted_ranks):
            continue
        paper_id = decision.get("candidate_id", "").strip()
        queue = queue_by_id.get(paper_id) or queue_by_rank.get(str(rank)) or {}
        provider_ids = parse_provider_ids(decision.get("provider_ids") or queue.get("provider_ids", ""))
        work = Work(
            paper_id=paper_id or queue.get("canonical_paper_id", "") or f"rank:{rank}",
            rank=rank,
            title=decision.get("title") or queue.get("title", ""),
            year=decision.get("year") or queue.get("year", ""),
            authors=decision.get("authors") or queue.get("authors", ""),
            venue=decision.get("venue") or queue.get("venue", ""),
            doi=(decision.get("doi") or queue.get("doi", "")).removeprefix("https://doi.org/"),
            arxiv_id=decision.get("arxiv_id") or queue.get("arxiv_id", ""),
            pmid=decision.get("pmid") or queue.get("pmid", ""),
            pmcid=_normalize_pmcid(decision.get("pmcid") or queue.get("pmcid", "")),
            openalex_id=provider_ids.get("openalex", "").removeprefix("https://openalex.org/"),
            semantic_scholar_id=provider_ids.get("semantic_scholar", ""),
            landing_url=decision.get("landing_url") or queue.get("landing_url", ""),
            pdf_url=decision.get("pdf_url") or queue.get("pdf_url", ""),
            is_open_access=boolish(decision.get("is_open_access") or queue.get("is_open_access", "")),
            screening_decision=decision_value,
            screening_confidence=decision.get("decision_confidence", ""),
            likely_paper_type=decision.get("likely_paper_type", ""),
            priority_score=decision.get("priority_score") or queue.get("priority_score", ""),
            source_row={**queue, **decision},
        )
        works.append(work)
    return sorted(works, key=lambda item: item.rank)


def build_queue(
    settings: Settings,
    rank_spec: str | None = None,
    decisions: Iterable[str] = ("include", "unclear"),
    out_dir: Path | None = None,
) -> Path:
    works = load_eligible_works(settings, decisions=decisions, rank_spec=rank_spec)
    _, artifacts = read_csv(settings.artifact_registry)
    by_paper: dict[str, set[str]] = {}
    for row in artifacts:
        if row.get("status") != "success":
            continue
        by_paper.setdefault(row.get("paper_id", ""), set()).add(row.get("artifact_type", ""))

    out_dir = out_dir or (settings.output_root / f"queue_{timestamp_id()}")
    out_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    for work in works:
        types = by_paper.get(work.paper_id, set())
        rows.append(
            {
                "paper_id": work.paper_id,
                "rank": work.rank,
                "title": work.title,
                "year": work.year,
                "authors": work.authors,
                "venue": work.venue,
                "doi": work.doi,
                "arxiv_id": work.arxiv_id,
                "pmid": work.pmid,
                "pmcid": work.pmcid,
                "openalex_id": work.openalex_id,
                "semantic_scholar_id": work.semantic_scholar_id,
                "landing_url": work.landing_url,
                "pdf_url": work.pdf_url,
                "is_open_access": work.is_open_access,
                "screening_decision": work.screening_decision,
                "screening_confidence": work.screening_confidence,
                "likely_paper_type": work.likely_paper_type,
                "priority_score": work.priority_score,
                "acquisition_status": "complete" if {"pdf", "jats_xml"} <= types or {"pdf", "tei_xml"} <= types else ("partial" if types else "pending"),
                "structured_status": "available" if types & {"jats_xml", "tei_xml"} else "missing",
                "pdf_status": "available" if "pdf" in types else "missing",
                "acquisition_batch_id": "",
                "ranking_position": "",
                "ranking_run_id": "",
                "ranking_source_sha256": "",
                "notes": "",
            }
        )
    queue_path = out_dir / "fulltext_queue.csv"
    atomic_write_csv(queue_path, FULLTEXT_QUEUE_FIELDS, rows)
    manifest = {
        "queue_path": _repo_rel(settings, queue_path),
        "created_from_decisions": _repo_rel(settings, settings.decisions_path),
        "decisions_sha256": sha256_file(settings.decisions_path),
        "source_queue": _repo_rel(settings, settings.queue_path),
        "source_queue_sha256": sha256_file(settings.queue_path),
        "rank_spec": rank_spec or "all eligible",
        "decisions": list(decisions),
        "eligible_works": len(rows),
    }
    write_json(out_dir / "queue_manifest.json", manifest)
    return queue_path


def build_queue_from_ranking(
    settings: Settings,
    ranking_path: Path,
    limit: int = 0,
    skip_complete: bool = False,
    allow_partial: bool = False,
    selection_policy: str = "exact-top-n",
    out_dir: Path | None = None,
) -> Path:
    if limit < 0 or limit > 50:
        raise ValueError("--limit must be between 1 and 50")
    if selection_policy not in ("exact-top-n", "first-n-eligible"):
        raise ValueError(f"Unknown selection_policy: {selection_policy}")

    _, ranking_rows = read_csv(ranking_path)
    if not ranking_rows:
        raise SystemExit(f"No rows found in ranking CSV: {ranking_path}")
    _, decision_rows = read_csv(settings.decisions_path)
    _, artifact_rows = read_csv(settings.artifact_registry)

    decisions_by_id: dict[str, dict[str, str]] = {}
    for row in decision_rows:
        cid = _detect_id(row, "candidate_id")
        if cid:
            decisions_by_id[cid] = row

    artifacts_by_paper: dict[str, set[str]] = {}
    for row in artifact_rows:
        if row.get("status") == "success":
            artifacts_by_paper.setdefault(row.get("paper_id", ""), set()).add(row.get("artifact_type", ""))

    effective_limit = limit if limit > 0 else min(len(ranking_rows), 50)
    ranking_run_id = _extract_ranking_run_id(ranking_path)
    ranking_source_sha256 = sha256_file(ranking_path)
    batch_id = f"FAB_{timestamp_id()}"
    errors: list[str] = []
    warnings: list[str] = []
    queue_rows: list[dict[str, str]] = []
    selection_rows: list[dict[str, str]] = []
    seen_candidate_ids: set[str] = set()

    for idx, ranking_row in enumerate(ranking_rows):
        candidate_id = _detect_id(ranking_row, "candidate_id", "canonical_paper_id", "paper_id")
        ranking_position = str(idx + 1)

        if not candidate_id:
            errors.append(f"Row {idx}: No detectable candidate_id")
            if selection_policy == "exact-top-n":
                break
            continue

        if candidate_id in seen_candidate_ids:
            errors.append(f"Row {idx}: Duplicate candidate_id: {candidate_id}")
            if selection_policy == "exact-top-n":
                break
            continue
        seen_candidate_ids.add(candidate_id)

        decision_row = decisions_by_id.get(candidate_id)
        if decision_row is None:
            errors.append(f"Row {idx}: Candidate {candidate_id} not found in decisions")
            if selection_policy == "exact-top-n":
                break
            continue

        decision = (decision_row.get("decision") or "").strip().lower()
        if decision not in ("include", "unclear"):
            errors.append(f"Row {idx}: Candidate {candidate_id} has decision '{decision}', not active")
            if selection_policy == "exact-top-n":
                break
            continue

        # Validate screening rank against authoritative decision
        authoritative_rank_str = (decision_row.get("rank") or "0").strip()
        try:
            authoritative_rank = int(authoritative_rank_str)
        except ValueError:
            authoritative_rank = 0
        if authoritative_rank <= 0:
            errors.append(f"Row {idx}: Authoritative rank for {candidate_id} is {authoritative_rank_str}, must be > 0")
            if selection_policy == "exact-top-n":
                break
            continue
        ranking_rank = _detect_screening_rank(ranking_row)
        if ranking_rank and ranking_rank != authoritative_rank:
            errors.append(f"Row {idx}: Screening rank mismatch for {candidate_id}: ranking says {ranking_rank}, decision says {authoritative_rank}")
            if selection_policy == "exact-top-n":
                break
            continue

        # Validate ranking paper_id alias if present
        ranking_paper_id = _detect_id(ranking_row, "paper_id", "canonical_paper_id")
        if ranking_paper_id and ranking_paper_id != candidate_id:
            errors.append(f"Row {idx}: paper_id '{ranking_paper_id}' does not match candidate_id '{candidate_id}'")
            if selection_policy == "exact-top-n":
                break
            continue

        # Identity conflict with stable ID priority
        conflict = _detect_identity_conflict(ranking_row, decision_row)
        if isinstance(conflict, str):
            errors.append(f"Row {idx}: Identity conflict for {candidate_id}: {conflict}")
            if selection_policy == "exact-top-n":
                break
            continue
        if isinstance(conflict, list):
            for w in conflict:
                warnings.append(f"Row {idx}: {w}")

        paper_id = candidate_id
        rank = authoritative_rank
        types = artifacts_by_paper.get(paper_id, set())

        if skip_complete:
            has_pdf = "pdf" in types
            has_xml = bool(types & {"jats_xml", "tei_xml"})
            if has_pdf and has_xml:
                continue

        if len(queue_rows) >= effective_limit:
            break

        queue_rows.append(_build_queue_row(ranking_row, decision_row, rank, paper_id, types, batch_id, ranking_position, ranking_run_id, ranking_source_sha256))
        selection_rows.append({
            "acquisition_batch_id": batch_id,
            "ranking_position": ranking_position,
            "candidate_id": candidate_id,
            "original_screening_rank": str(rank),
            "title": ranking_row.get("title") or decision_row.get("title", ""),
            "priority_score": ranking_row.get("priority_score") or decision_row.get("priority_score", "") or "",
            "ranking_run_id": ranking_run_id,
        })

        if selection_policy == "exact-top-n" and len(queue_rows) >= effective_limit:
            break

    if not allow_partial and errors:
        raise QueueValidationError(
            f"Queue validation failed with {len(errors)} error(s):\n" + "\n".join(errors)
        )

    validation_status = "passed" if not errors else ("partial" if allow_partial else "failed")

    out_dir = out_dir or (settings.output_root / f"queue_{timestamp_id()}")
    out_dir.mkdir(parents=True, exist_ok=False)
    queue_path = out_dir / "fulltext_queue.csv"
    queue_sha256 = sha256_file(queue_path) if queue_path.exists() else ""
    atomic_write_csv(queue_path, FULLTEXT_QUEUE_FIELDS, queue_rows)
    queue_sha256 = sha256_file(queue_path)

    write_json(
        out_dir / "queue_manifest.json",
        {
            "queue_path": _repo_rel(settings, queue_path),
            "ranking_source": _repo_rel(settings, ranking_path),
            "ranking_source_sha256": ranking_source_sha256,
            "queue_sha256": queue_sha256,
            "source_decisions": _repo_rel(settings, settings.decisions_path),
            "source_decisions_sha256": sha256_file(settings.decisions_path),
            "source_screening_queue": _repo_rel(settings, settings.queue_path),
            "source_screening_queue_sha256": sha256_file(settings.queue_path),
            "source_active_scores_sha256": _scores_sha256(settings),
            "selection_policy": selection_policy,
            "requested_limit": limit,
            "source_row_count": len(ranking_rows),
            "effective_limit": effective_limit,
            "selected_count": len(queue_rows),
            "skip_complete": skip_complete,
            "validation_status": validation_status,
        },
    )

    if errors:
        write_json(out_dir / "ranking_validation_errors.json", {"errors": errors, "warnings": warnings})

    _create_batch_snapshot(settings, batch_id, selection_rows, validation_status, effective_limit, len(queue_rows), queue_path, ranking_path, ranking_source_sha256, queue_sha256, limit, skip_complete, selection_policy, len(ranking_rows), settings)

    _append_acquisition_batch(settings, ranking_path, ranking_source_sha256, queue_path, queue_sha256, validation_status, limit, len(ranking_rows), effective_limit, len(queue_rows), skip_complete, selection_policy)

    return queue_path


def _extract_ranking_run_id(ranking_path: Path) -> str:
    for part in ranking_path.parts:
        if re.match(r"^(RANK|BOOTSTRAP)_", part):
            return part
    return ""


def _scores_sha256(settings: Settings) -> str:
    scores_path = settings.repo / "data/curated/ranking/paper_priority_scores.csv"
    if scores_path.exists():
        return sha256_file(scores_path)
    return ""


def _detect_id(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def _detect_screening_rank(row: dict[str, str]) -> int:
    raw = row.get("original_screening_rank") or row.get("screening_rank") or row.get("rank") or ""
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _stable_ids_match(ranking_row: dict[str, str], decision_row: dict[str, str]) -> bool:
    for key, transform in [
        ("doi", lambda v: v.strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")),
        ("arxiv_id", lambda v: v.strip().lower()),
        ("pmid", lambda v: v.strip()),
    ]:
        rv = transform(ranking_row.get(key, ""))
        dv = transform(decision_row.get(key, ""))
        if rv and dv and rv == dv:
            return True
    return False


def _detect_identity_conflict(ranking_row: dict[str, str], decision_row: dict[str, str]) -> str | list[str] | None:
    ranking_doi = (ranking_row.get("doi") or "").strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")
    decision_doi = (decision_row.get("doi") or "").strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")
    if ranking_doi and decision_doi and ranking_doi != decision_doi:
        return f"DOI mismatch: {ranking_doi} vs {decision_doi}"

    if _stable_ids_match(ranking_row, decision_row):
        warnings: list[str] = []
        ranking_title = (ranking_row.get("title") or "").strip().lower()
        decision_title = (decision_row.get("title") or "").strip().lower()
        if ranking_title and decision_title and ranking_title != decision_title:
            warnings.append(f"Title differs despite stable ID match")
        ranking_year = (ranking_row.get("year") or "").strip()
        decision_year = (decision_row.get("year") or "").strip()
        if ranking_year and decision_year and ranking_year != decision_year:
            warnings.append(f"Year differs despite stable ID match: {ranking_year} vs {decision_year}")
        return warnings if warnings else None

    ranking_title = (ranking_row.get("title") or "").strip().lower()
    decision_title = (decision_row.get("title") or "").strip().lower()
    if ranking_title and decision_title and ranking_title != decision_title:
        ranking_short = ranking_title[:60]
        decision_short = decision_title[:60]
        return f"Title mismatch: '{ranking_short}...' vs '{decision_short}...'"

    ranking_year = (ranking_row.get("year") or "").strip()
    decision_year = (decision_row.get("year") or "").strip()
    if ranking_year and decision_year and ranking_year != decision_year:
        return f"Year mismatch: {ranking_year} vs {decision_year}"

    return None


def _build_queue_row(
    ranking_row: dict[str, str],
    decision_row: dict[str, str],
    rank: int,
    paper_id: str,
    types: set[str],
    batch_id: str,
    ranking_position: str,
    ranking_run_id: str,
    ranking_source_sha256: str,
) -> dict[str, str]:
    provider_ids = parse_provider_ids(ranking_row.get("provider_ids") or decision_row.get("provider_ids", ""))
    screening_decision = (decision_row.get("decision") or "").strip().lower()
    priority_score = ranking_row.get("priority_score") or decision_row.get("priority_score") or ""

    return {
        "paper_id": paper_id,
        "rank": str(rank),
        "title": ranking_row.get("title") or decision_row.get("title", ""),
        "year": ranking_row.get("year") or decision_row.get("year", ""),
        "authors": ranking_row.get("authors") or decision_row.get("authors", ""),
        "venue": ranking_row.get("venue") or decision_row.get("venue", ""),
        "doi": (ranking_row.get("doi") or decision_row.get("doi", "")).removeprefix("https://doi.org/"),
        "arxiv_id": ranking_row.get("arxiv_id") or decision_row.get("arxiv_id", ""),
        "pmid": ranking_row.get("pmid") or decision_row.get("pmid", ""),
        "pmcid": _normalize_pmcid(ranking_row.get("pmcid") or decision_row.get("pmcid", "")),
        "openalex_id": provider_ids.get("openalex", "").removeprefix("https://openalex.org/"),
        "semantic_scholar_id": provider_ids.get("semantic_scholar", ""),
        "landing_url": ranking_row.get("landing_url") or decision_row.get("landing_url", ""),
        "pdf_url": ranking_row.get("pdf_url") or decision_row.get("pdf_url", ""),
        "is_open_access": boolish(ranking_row.get("is_open_access") or decision_row.get("is_open_access", "")),
        "screening_decision": screening_decision,
        "screening_confidence": decision_row.get("decision_confidence", ""),
        "likely_paper_type": ranking_row.get("likely_paper_type") or decision_row.get("likely_paper_type", ""),
        "priority_score": priority_score,
        "acquisition_status": "complete" if {"pdf", "jats_xml"} <= types or {"pdf", "tei_xml"} <= types else ("partial" if types else "pending"),
        "structured_status": "available" if types & {"jats_xml", "tei_xml"} else "missing",
        "pdf_status": "available" if "pdf" in types else "missing",
        "acquisition_batch_id": batch_id,
        "ranking_position": ranking_position,
        "ranking_run_id": ranking_run_id,
        "ranking_source_sha256": ranking_source_sha256,
        "notes": "",
    }


def _create_batch_snapshot(
    settings: Settings,
    batch_id: str,
    selection_rows: list[dict[str, str]],
    validation_status: str,
    effective_limit: int,
    selected_count: int,
    queue_path: Path,
    ranking_path: Path,
    ranking_source_sha256: str,
    queue_sha256: str,
    limit: int,
    skip_complete: bool,
    selection_policy: str,
    source_row_count: int,
    _settings: Settings,
) -> Path:
    snapshot_dir = settings.repo / "data/curated/fulltext/acquisition_batches" / batch_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    selection_path = snapshot_dir / "selection.csv"
    atomic_write_csv(selection_path, SELECTION_FIELDS, selection_rows)

    ordered_ids = [row["candidate_id"] for row in selection_rows]

    manifest = {
        "acquisition_batch_id": batch_id,
        "ranking_source": _repo_rel(settings, ranking_path),
        "ranking_source_sha256": ranking_source_sha256,
        "queue_path": _repo_rel(settings, queue_path),
        "queue_sha256": queue_sha256,
        "source_decisions_sha256": sha256_file(settings.decisions_path),
        "source_screening_queue_sha256": sha256_file(settings.queue_path),
        "source_active_scores_sha256": _scores_sha256(settings),
        "ordered_candidate_ids": ordered_ids,
        "selection_policy": selection_policy,
        "requested_limit": limit,
        "source_row_count": source_row_count,
        "effective_limit": effective_limit,
        "selected_count": selected_count,
        "skip_complete": skip_complete,
        "validation_status": validation_status,
        "created_at": now_utc(),
    }
    write_json(snapshot_dir / "manifest.json", manifest)
    return snapshot_dir


def _append_acquisition_batch(
    settings: Settings,
    ranking_path: Path,
    ranking_source_sha256: str,
    queue_path: Path,
    queue_sha256: str,
    validation_status: str,
    limit: int,
    source_row_count: int,
    effective_limit: int,
    selected_count: int,
    skip_complete: bool,
    selection_policy: str,
) -> None:
    batch_path = settings.repo / "data/curated/fulltext/fulltext_acquisition_batches.csv"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_id = f"FAB_{timestamp_id()}"
    append_csv(
        batch_path,
        ACQUISITION_BATCH_FIELDS,
        [
            {
                "batch_id": batch_id,
                "ranking_source": _repo_rel(settings, ranking_path),
                "ranking_source_sha256": ranking_source_sha256,
                "queue_path": _repo_rel(settings, queue_path),
                "queue_sha256": queue_sha256,
                "selection_policy": selection_policy,
                "requested_limit": str(limit),
                "source_row_count": str(source_row_count),
                "effective_limit": str(effective_limit),
                "selected_count": str(selected_count),
                "skip_complete": str(skip_complete).lower(),
                "validation_status": validation_status,
                "created_at": now_utc(),
                "notes": "",
            }
        ],
    )


def work_from_queue_row(row: dict[str, str]) -> Work:
    return Work(
        paper_id=row.get("paper_id", ""),
        rank=int(row.get("rank") or 0),
        title=row.get("title", ""),
        year=row.get("year", ""),
        authors=row.get("authors", ""),
        venue=row.get("venue", ""),
        doi=row.get("doi", ""),
        arxiv_id=row.get("arxiv_id", ""),
        pmid=row.get("pmid", ""),
        pmcid=_normalize_pmcid(row.get("pmcid", "")),
        openalex_id=row.get("openalex_id", ""),
        semantic_scholar_id=row.get("semantic_scholar_id", ""),
        landing_url=row.get("landing_url", ""),
        pdf_url=row.get("pdf_url", ""),
        is_open_access=boolish(row.get("is_open_access", "")),
        screening_decision=row.get("screening_decision", ""),
        screening_confidence=row.get("screening_confidence", ""),
        likely_paper_type=row.get("likely_paper_type", ""),
        priority_score=row.get("priority_score", ""),
        source_row=row,
    )


def _normalize_pmcid(value: str) -> str:
    value = (value or "").strip().upper()
    if value and not value.startswith("PMC"):
        value = f"PMC{value}"
    return value
