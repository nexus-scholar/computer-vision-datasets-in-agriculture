from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from .acquisition import acquire_queue, import_local_artifact
from .config import load_settings
from .http_client import PoliteSession
from .io_utils import atomic_write_csv, parse_rank_spec, read_csv, redact_secrets, timestamp_id, write_json
from .models import Work
from .preflight import inspect_pdf
from .processing import process_registered_artifacts, render_pages
from .queueing import build_queue, load_eligible_works, work_from_queue_row
from .reviewing import finalize_review, prepare_review
from .resolvers import resolve_candidates
from .schema import CANDIDATE_FIELDS
from .state import build_review_queue, fulltext_status, validate_fulltext


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agri-fulltext", description="Legal full-text acquisition and structured PDF workflow.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--config", type=Path, help="fulltext.toml path")
    sub = parser.add_subparsers(dest="command", required=True)

    queue = sub.add_parser("queue", help="Build an acquisition queue from active title/abstract decisions")
    queue.add_argument("--ranks", help="Ranks N, N-M, or comma-separated ranges")
    queue.add_argument("--decisions", default="include,unclear")
    queue.add_argument("--out", type=Path)

    resolve = sub.add_parser("resolve", help="Resolve and score legal full-text candidates without downloading")
    resolve.add_argument("queue", type=Path)
    resolve.add_argument("--out", type=Path)

    acquire = sub.add_parser("acquire", help="Resolve and download legal full-text artifacts")
    acquire.add_argument("queue", type=Path)
    acquire.add_argument("--artifact-set", choices=["both", "pdf", "structured"], default="both")
    acquire.add_argument("--refresh", action="store_true")
    acquire.add_argument("--allow-unknown-rights", action="store_true")
    acquire.add_argument("--out", type=Path)

    manual = sub.add_parser("import", help="Register a lawfully obtained local PDF/XML")
    manual.add_argument("file", type=Path)
    manual.add_argument("--paper-id")
    manual.add_argument("--rank", type=int)
    manual.add_argument("--rights-status", choices=["open_license", "free_to_read_unknown_reuse", "local_research_only", "restricted"], required=True)
    manual.add_argument("--license", default="")
    manual.add_argument("--version", default="user_supplied")
    manual.add_argument("--notes", default="")

    preflight = sub.add_parser("preflight", help="Classify one PDF before extraction")
    preflight.add_argument("pdf", type=Path)
    preflight.add_argument("--out", type=Path)

    process = sub.add_parser("process", help="Process registered artifacts with Docling, GROBID and XML normalization")
    process.add_argument("--ranks")
    process.add_argument("--paper-id", action="append", default=[])
    process.add_argument("--no-docling", action="store_true")
    process.add_argument("--no-grobid", action="store_true")
    process.add_argument("--refresh", action="store_true")
    process.add_argument("--out", type=Path)

    render = sub.add_parser("render-pages", help="Render selected PDF pages for visual verification")
    render.add_argument("pdf", type=Path)
    render.add_argument("--pages", required=True, help="Pages N, N-M, or comma-separated ranges")
    render.add_argument("--out", type=Path, required=True)
    render.add_argument("--dpi", type=int, default=160)

    review = sub.add_parser("review-queue", help="Build a full-text review queue from processed artifacts")
    review.add_argument("--out", type=Path)

    prepare_review_parser = sub.add_parser("prepare-review", help="Prepare one deterministic full-text review workspace")
    prepare_review_parser.add_argument("identifier", help="Screening rank or canonical paper ID")
    prepare_review_parser.add_argument("--out", type=Path)

    finalize_review_parser = sub.add_parser("finalize-review", help="Validate and append one full-text decision event")
    finalize_review_parser.add_argument("decision", type=Path)

    sub.add_parser("status", help="Summarize acquisition and processing state")
    validate = sub.add_parser("validate", help="Validate full-text registries, hashes and extraction outputs")
    validate.add_argument("--json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(args.repo, args.config)

    if args.command == "queue":
        path = build_queue(
            settings,
            rank_spec=args.ranks,
            decisions=[item.strip() for item in args.decisions.split(",") if item.strip()],
            out_dir=args.out,
        )
        print(path)
        return 0

    if args.command == "resolve":
        _, rows = read_csv(args.queue)
        session = PoliteSession(max_retries=settings.max_retries)
        session.headers.update({"User-Agent": settings.user_agent})
        all_candidates = []
        errors = []
        for row in rows:
            candidates, work_errors = resolve_candidates(settings, work_from_queue_row(row), session)
            all_candidates.extend(_safe_candidate(candidate) for candidate in candidates)
            errors.extend(work_errors)
        out = args.out or (settings.output_root / f"resolution_{timestamp_id()}")
        out.mkdir(parents=True, exist_ok=False)
        atomic_write_csv(out / "candidates.csv", CANDIDATE_FIELDS, all_candidates)
        atomic_write_csv(out / "resolver_errors.csv", ["paper_id", "source", "error"], errors)
        write_json(out / "resolution_manifest.json", {"queue": str(args.queue), "candidates": len(all_candidates), "errors": len(errors)})
        print(out)
        return 0

    if args.command == "acquire":
        path = acquire_queue(
            settings,
            args.queue,
            artifact_set=args.artifact_set,
            refresh=args.refresh,
            allow_unknown_rights=args.allow_unknown_rights,
            out_dir=args.out,
        )
        print(path)
        return 0

    if args.command == "import":
        work = _find_work(settings, args.paper_id, args.rank)
        row = import_local_artifact(
            settings,
            work,
            args.file,
            rights_status=args.rights_status,
            license_value=args.license,
            version=args.version,
            notes=args.notes,
        )
        print(json.dumps(row, indent=2, ensure_ascii=False))
        return 0

    if args.command == "preflight":
        result = inspect_pdf(args.pdf)
        if args.out:
            write_json(args.out, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "process":
        path = process_registered_artifacts(
            settings,
            rank_spec=args.ranks,
            paper_ids=args.paper_id,
            run_docling=not args.no_docling,
            run_grobid=not args.no_grobid,
            out_dir=args.out,
            refresh=args.refresh,
        )
        print(path)
        return 0

    if args.command == "render-pages":
        pages = parse_rank_spec(args.pages)
        if not pages:
            raise SystemExit("No pages requested")
        paths = render_pages(args.pdf, args.out, pages, args.dpi)
        print("\n".join(str(path) for path in paths))
        return 0

    if args.command == "review-queue":
        path = build_review_queue(settings, args.out)
        print(path)
        return 0

    if args.command == "prepare-review":
        path = prepare_review(settings, args.identifier, args.out)
        print(path)
        return 0

    if args.command == "finalize-review":
        result = finalize_review(settings, args.decision)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "status":
        print(json.dumps(fulltext_status(settings), indent=2, ensure_ascii=False))
        return 0

    if args.command == "validate":
        result = validate_fulltext(settings)
        if args.json:
            write_json(args.json, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["passed"] else 1

    parser.error(f"Unknown command {args.command}")
    return 2


def _find_work(settings, paper_id: str | None, rank: int | None) -> Work:
    works = load_eligible_works(settings)
    for work in works:
        if paper_id and work.paper_id == paper_id:
            return work
        if rank and work.rank == rank:
            return work
    raise SystemExit("No eligible work matches --paper-id/--rank")


def _safe_candidate(candidate):
    row = candidate.as_row()
    row["url"] = redact_secrets(str(row.get("url", "")))
    return row


if __name__ == "__main__":
    raise SystemExit(main())
