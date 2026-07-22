from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import Settings
from .io_utils import atomic_write_csv, boolish, parse_rank_spec, read_csv, sha256_file, timestamp_id, write_json
from .models import Work
from .schema import FULLTEXT_QUEUE_FIELDS


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
