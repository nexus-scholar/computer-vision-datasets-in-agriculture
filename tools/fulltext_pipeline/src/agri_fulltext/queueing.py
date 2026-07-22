from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import Settings
from .io_utils import append_csv, atomic_write_csv, boolish, now_utc, parse_rank_spec, read_csv, sha256_file, timestamp_id, write_json
from .models import Work
from .schema import ACQUISITION_BATCH_FIELDS, FULLTEXT_QUEUE_FIELDS


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
                "notes": "",
            }
        )
    queue_path = out_dir / "fulltext_queue.csv"
    atomic_write_csv(queue_path, FULLTEXT_QUEUE_FIELDS, rows)
    manifest = {
        "queue_path": str(queue_path),
        "created_from_decisions": str(settings.decisions_path),
        "decisions_sha256": sha256_file(settings.decisions_path),
        "source_queue": str(settings.queue_path),
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
    out_dir: Path | None = None,
) -> Path:
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
    errors: list[str] = []
    queue_rows: list[dict[str, str]] = []
    seen_candidate_ids: set[str] = set()

    for idx, ranking_row in enumerate(ranking_rows):
        if len(queue_rows) >= effective_limit:
            break

        candidate_id = _detect_id(ranking_row, "candidate_id", "canonical_paper_id", "paper_id")
        if not candidate_id:
            errors.append(f"Row {idx}: No detectable candidate_id")
            continue

        if candidate_id in seen_candidate_ids:
            errors.append(f"Row {idx}: Duplicate candidate_id: {candidate_id}")
            continue
        seen_candidate_ids.add(candidate_id)

        decision_row = decisions_by_id.get(candidate_id)
        if decision_row is None:
            errors.append(f"Row {idx}: Candidate {candidate_id} not found in decisions at {settings.decisions_path}")
            continue

        decision = (decision_row.get("decision") or "").strip().lower()
        if decision not in ("include", "unclear"):
            errors.append(f"Row {idx}: Candidate {candidate_id} has decision '{decision}', not active")
            continue

        conflict = _detect_identity_conflict(ranking_row, decision_row)
        if conflict:
            errors.append(f"Row {idx}: Identity conflict for {candidate_id}: {conflict}")
            continue

        rank = _detect_screening_rank(ranking_row)
        paper_id = _detect_id(ranking_row, "paper_id", "canonical_paper_id") or candidate_id or f"rank:{rank}"
        types = artifacts_by_paper.get(paper_id, set())

        if skip_complete:
            has_pdf = "pdf" in types
            has_xml = bool(types & {"jats_xml", "tei_xml"})
            if has_pdf and has_xml:
                continue

        queue_rows.append(_build_queue_row(ranking_row, decision_row, rank, paper_id, types))

    ranking_source_sha256 = sha256_file(ranking_path)
    out_dir = out_dir or (settings.output_root / f"queue_{timestamp_id()}")
    out_dir.mkdir(parents=True, exist_ok=False)
    queue_path = out_dir / "fulltext_queue.csv"
    atomic_write_csv(queue_path, FULLTEXT_QUEUE_FIELDS, queue_rows)

    write_json(
        out_dir / "queue_manifest.json",
        {
            "queue_path": str(queue_path),
            "ranking_source": str(ranking_path),
            "ranking_source_sha256": ranking_source_sha256,
            "source_decisions": str(settings.decisions_path),
            "source_decisions_sha256": sha256_file(settings.decisions_path),
            "limit": limit,
            "skip_complete": skip_complete,
            "eligible_works": len(queue_rows),
            "validation_errors": len(errors),
        },
    )

    if errors:
        write_json(out_dir / "ranking_validation_errors.json", errors)

    _append_acquisition_batch(settings, ranking_path, ranking_source_sha256, queue_path, limit, skip_complete, len(queue_rows), len(errors))

    return queue_path


def _detect_id(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def _detect_screening_rank(row: dict[str, str]) -> int:
    raw = row.get("original_screening_rank") or row.get("screening_rank") or row.get("rank") or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def _detect_identity_conflict(ranking_row: dict[str, str], decision_row: dict[str, str]) -> str | None:
    ranking_doi = (ranking_row.get("doi") or "").strip().lower().removeprefix("https://doi.org/")
    decision_doi = (decision_row.get("doi") or "").strip().lower().removeprefix("https://doi.org/")
    if ranking_doi and decision_doi and ranking_doi != decision_doi:
        return f"DOI mismatch: {ranking_doi} vs {decision_doi}"

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


def _build_queue_row(ranking_row: dict[str, str], decision_row: dict[str, str], rank: int, paper_id: str, types: set[str]) -> dict[str, str]:
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
        "notes": "",
    }


def _append_acquisition_batch(
    settings: Settings,
    ranking_path: Path,
    ranking_source_sha256: str,
    queue_path: Path,
    limit: int,
    skip_complete: bool,
    paper_count: int,
    error_count: int,
) -> None:
    batch_path = settings.repo / "data/curated/fulltext/fulltext_acquisition_batches.csv"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    append_csv(
        batch_path,
        ACQUISITION_BATCH_FIELDS,
        [
            {
                "batch_id": f"FAB_{timestamp_id()}",
                "ranking_source": str(ranking_path),
                "ranking_source_sha256": ranking_source_sha256,
                "queue_path": str(queue_path),
                "limit": str(limit),
                "skip_complete": str(skip_complete).lower(),
                "created_at": now_utc(),
                "paper_count": str(paper_count),
                "error_count": str(error_count),
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
