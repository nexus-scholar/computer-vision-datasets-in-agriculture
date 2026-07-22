from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

import fitz
import requests
from lxml import etree

from . import __version__
from .config import Settings
from .io_utils import append_csv, atomic_write_csv, now_utc, parse_rank_spec, read_csv, safe_segment, sha256_file, sha256_text, timestamp_id, write_json
from .preflight import inspect_pdf
from .schema import EXTRACTION_REGISTRY_FIELDS
from .xml_extract import xml_to_outputs


def process_registered_artifacts(
    settings: Settings,
    rank_spec: str | None = None,
    paper_ids: Iterable[str] | None = None,
    run_docling: bool = True,
    run_grobid: bool = True,
    out_dir: Path | None = None,
    refresh: bool = False,
) -> Path:
    wanted_ranks = parse_rank_spec(rank_spec)
    wanted_ids = set(paper_ids or [])
    _, registry_rows = read_csv(settings.artifact_registry)
    active = _active_artifacts(settings, registry_rows)
    papers: dict[str, dict[str, dict[str, str]]] = {}
    for row in active.values():
        rank = int(row.get("rank") or 0)
        paper_id = row.get("paper_id", "")
        if wanted_ranks is not None and rank not in wanted_ranks:
            continue
        if wanted_ids and paper_id not in wanted_ids:
            continue
        papers.setdefault(paper_id, {})[row.get("artifact_type", "")] = row

    run_id = f"FTP_{timestamp_id()}"
    out_dir = out_dir or (settings.processing_root / run_id)
    out_dir.mkdir(parents=True, exist_ok=False)
    extraction_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for paper_id, artifacts in sorted(papers.items(), key=lambda item: int(next(iter(item[1].values())).get("rank") or 0)):
        metadata = next(iter(artifacts.values()))
        paper_dir = out_dir / safe_segment(paper_id)
        paper_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = paper_dir / "manifest.json"
        if manifest_path.exists() and not refresh:
            continue
        result = _process_one(settings, paper_id, artifacts, paper_dir, run_id, run_docling, run_grobid)
        extraction_rows.append(result["registry_row"])
        summary_rows.append(result["summary_row"])

    if extraction_rows:
        append_csv(settings.extraction_registry, EXTRACTION_REGISTRY_FIELDS, extraction_rows)
    atomic_write_csv(
        out_dir / "processing_summary.csv",
        [
            "paper_id", "rank", "title", "source_pdf", "source_xml", "preflight_class", "docling_status",
            "grobid_status", "publisher_xml_status", "qa_status", "output_dir", "warnings",
        ],
        summary_rows,
    )
    run_manifest = {
        "run_id": run_id,
        "tool_version": __version__,
        "created_at": now_utc(),
        "artifact_registry": str(settings.artifact_registry),
        "artifact_registry_sha256": sha256_file(settings.artifact_registry),
        "rank_spec": rank_spec or "all registered artifacts",
        "paper_ids": sorted(wanted_ids),
        "run_docling": run_docling,
        "run_grobid": run_grobid,
        "processed_papers": len(summary_rows),
    }
    write_json(out_dir / "run_manifest.json", run_manifest)
    _processing_report(out_dir / "run_report.md", run_manifest, summary_rows)
    return out_dir


def render_pages(pdf_path: Path, output_dir: Path, pages: Iterable[int], dpi: int = 160) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    rendered: list[Path] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page_number in sorted(set(pages)):
        if page_number < 1 or page_number > doc.page_count:
            raise ValueError(f"Page {page_number} outside 1-{doc.page_count}")
        page = doc.load_page(page_number - 1)
        output = output_dir / f"page_{page_number:04d}.png"
        page.get_pixmap(matrix=matrix, alpha=False).save(output)
        rendered.append(output)
    return rendered


def _process_one(
    settings: Settings,
    paper_id: str,
    artifacts: dict[str, dict[str, str]],
    paper_dir: Path,
    run_id: str,
    run_docling: bool,
    run_grobid: bool,
) -> dict[str, Any]:
    pdf_row = artifacts.get("pdf")
    xml_row = artifacts.get("jats_xml") or artifacts.get("tei_xml") or artifacts.get("xml")
    metadata = pdf_row or xml_row or {}
    rank = int(metadata.get("rank") or 0)
    title = metadata.get("title", "")
    warnings: list[str] = []
    preflight: dict[str, Any] = {}
    docling_status = "not_run"
    grobid_status = "not_run"
    publisher_xml_status = "not_available"
    docling_metrics: dict[str, Any] = {}
    grobid_metrics: dict[str, Any] = {}
    publisher_metrics: dict[str, Any] = {}

    source_manifest = {
        "paper_id": paper_id,
        "rank": rank,
        "title": title,
        "artifacts": artifacts,
        "created_at": now_utc(),
    }
    write_json(paper_dir / "source_manifest.json", source_manifest)

    if xml_row:
        xml_path = settings.repo / xml_row["stored_path"]
        publisher_dir = paper_dir / "publisher_xml"
        try:
            publisher_metrics = xml_to_outputs(xml_path, publisher_dir, paper_id, xml_row["sha256"])
            publisher_xml_status = "success"
        except Exception as exc:
            publisher_xml_status = "failed"
            warnings.append(f"publisher XML: {type(exc).__name__}: {exc}")

    if pdf_row:
        pdf_path = settings.repo / pdf_row["stored_path"]
        try:
            preflight = inspect_pdf(pdf_path)
            write_json(paper_dir / "qa/preflight.json", preflight)
        except Exception as exc:
            preflight = {"classification": "failed", "error": f"{type(exc).__name__}: {exc}"}
            write_json(paper_dir / "qa/preflight.json", preflight)
            warnings.append(f"preflight: {type(exc).__name__}: {exc}")

        if run_docling:
            try:
                docling_metrics = _run_docling(settings, pdf_path, paper_dir / "docling", preflight)
                docling_status = "success"
            except Exception as exc:
                docling_status = "failed"
                warnings.append(f"docling: {type(exc).__name__}: {exc}")
        if run_grobid:
            try:
                grobid_metrics = _run_grobid(settings, pdf_path, paper_dir / "grobid", paper_id, pdf_row["sha256"])
                grobid_status = "success"
            except Exception as exc:
                grobid_status = "failed"
                warnings.append(f"grobid: {type(exc).__name__}: {exc}")

    llm_metrics = _build_llm_bundle(
        paper_dir,
        paper_id,
        rank,
        title,
        pdf_source_sha256=(pdf_row or {}).get("sha256", ""),
        xml_source_sha256=(xml_row or {}).get("sha256", ""),
        publisher_xml_status=publisher_xml_status,
        docling_status=docling_status,
        grobid_status=grobid_status,
    )
    qa = _quality_assessment(preflight, publisher_metrics, docling_metrics, grobid_metrics, llm_metrics, warnings)
    write_json(paper_dir / "qa/extraction_quality.json", qa)

    manifest = {
        "paper_id": paper_id,
        "rank": rank,
        "title": title,
        "run_id": run_id,
        "tool_version": __version__,
        "created_at": now_utc(),
        "source_artifacts": artifacts,
        "preflight": preflight,
        "publisher_xml": {"status": publisher_xml_status, **publisher_metrics},
        "docling": {"status": docling_status, **docling_metrics},
        "grobid": {"status": grobid_status, **grobid_metrics},
        "llm_bundle": llm_metrics,
        "quality": qa,
        "warnings": warnings,
    }
    manifest_path = paper_dir / "manifest.json"
    write_json(manifest_path, manifest)
    source_row = pdf_row or xml_row or {}
    extraction_id = "FTE_" + sha256_text(f"{paper_id}|{source_row.get('sha256','')}|{run_id}")[:20]
    registry_row = {
        "extraction_id": extraction_id,
        "paper_id": paper_id,
        "rank": rank,
        "title": title,
        "source_sha256": source_row.get("sha256", ""),
        "source_artifact_type": source_row.get("artifact_type", ""),
        "output_dir": str(paper_dir.relative_to(settings.repo)).replace("\\", "/"),
        "docling_status": docling_status,
        "grobid_status": grobid_status,
        "publisher_xml_status": publisher_xml_status,
        "preflight_class": preflight.get("classification", "not_available"),
        "qa_status": qa["status"],
        "processor_version": __version__,
        "created_at": now_utc(),
        "run_id": run_id,
        "manifest_sha256": sha256_file(manifest_path),
        "notes": "; ".join(warnings),
    }
    return {
        "registry_row": registry_row,
        "summary_row": {
            "paper_id": paper_id,
            "rank": rank,
            "title": title,
            "source_pdf": pdf_row.get("stored_path", "") if pdf_row else "",
            "source_xml": xml_row.get("stored_path", "") if xml_row else "",
            "preflight_class": preflight.get("classification", "not_available"),
            "docling_status": docling_status,
            "grobid_status": grobid_status,
            "publisher_xml_status": publisher_xml_status,
            "qa_status": qa["status"],
            "output_dir": str(paper_dir.relative_to(settings.repo)).replace("\\", "/"),
            "warnings": "; ".join(warnings),
        },
    }


def _run_docling(settings: Settings, pdf_path: Path, output_dir: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = settings.docling_mode.lower()
    if mode == "remote":
        if not settings.docling_service_url:
            raise ValueError("DOCLING_SERVICE_URL is required for remote mode")
        command = [
            "docling", "convert-remote", str(pdf_path), "--service-url", settings.docling_service_url,
            "--from", "pdf", "--to", "json", "--to", "md", "--to", "html", "--to", "chunks",
            "--chunks-type", "hierarchical", "--image-export-mode", "referenced", "--tables",
            "--pipeline", "standard", "--document-timeout", str(settings.docling_timeout_seconds),
            "--output", str(output_dir), "--abort-on-error", "--timeout", str(settings.docling_timeout_seconds),
        ]
        _append_docling_ocr_flags(command, preflight)
    elif mode == "local":
        command = [
            "docling", "convert", str(pdf_path), "--from", "pdf", "--to", "json", "--to", "md",
            "--to", "html", "--to", "chunks", "--chunks-type", "hierarchical",
            "--image-export-mode", "referenced", "--tables", "--table-mode", "accurate",
            "--pipeline", "standard", "--device", settings.docling_device, "--num-threads", str(settings.docling_threads),
            "--document-timeout", str(settings.docling_timeout_seconds), "--output", str(output_dir), "--abort-on-error",
        ]
        _append_docling_ocr_flags(command, preflight)
    else:
        raise ValueError(f"Unknown Docling mode: {settings.docling_mode}")
    completed = subprocess.run(command, text=True, capture_output=True, timeout=settings.docling_timeout_seconds + 120)
    (output_dir / "docling_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "docling_stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Docling exited {completed.returncode}; see docling_stderr.log")
    normalized = _normalize_docling_outputs(output_dir, pdf_path.stem)
    normalized["command"] = command
    return normalized



def _append_docling_ocr_flags(command: list[str], preflight: dict[str, Any]) -> None:
    """Apply the same preflight-driven OCR policy to local and remote Docling."""
    command.append("--ocr" if preflight.get("recommended_ocr") else "--no-ocr")
    if preflight.get("force_ocr_recommended"):
        command.append("--force-ocr")


def _run_grobid(settings: Settings, pdf_path: Path, output_dir: Path, paper_id: str, source_sha256: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    health = requests.get(f"{settings.grobid_url.rstrip('/')}/api/isalive", timeout=10)
    health.raise_for_status()
    data = [
        ("consolidateHeader", "0"),
        ("consolidateCitations", "0"),
        ("includeRawCitations", "1"),
        ("includeRawAffiliations", "1"),
        ("segmentSentences", "1"),
        ("teiCoordinates", "figure"),
        ("teiCoordinates", "biblStruct"),
        ("teiCoordinates", "ref"),
        ("teiCoordinates", "formula"),
    ]
    with pdf_path.open("rb") as handle:
        response = requests.post(
            f"{settings.grobid_url.rstrip('/')}/api/processFulltextDocument",
            files={"input": (pdf_path.name, handle, "application/pdf")},
            data=data,
            timeout=settings.docling_timeout_seconds,
        )
    response.raise_for_status()
    tei_path = output_dir / "fulltext.tei.xml"
    tei_path.write_bytes(response.content)
    etree.parse(str(tei_path))
    normalized_dir = output_dir / "normalized"
    metrics = xml_to_outputs(tei_path, normalized_dir, paper_id, source_sha256)
    return {"tei_path": str(tei_path), **metrics}


def _normalize_docling_outputs(output_dir: Path, source_stem: str) -> dict[str, Any]:
    files = [path for path in output_dir.rglob("*") if path.is_file() and not path.name.endswith(".log")]
    selected: dict[str, Path] = {}
    for path in files:
        lower = path.name.lower()
        if lower.endswith(".md") and "document.md" not in selected:
            selected["document.md"] = path
        elif lower.endswith(".html") and "document.html" not in selected:
            selected["document.html"] = path
        elif "chunk" in lower and lower.endswith((".json", ".jsonl")):
            selected.setdefault("chunks.raw" + path.suffix.lower(), path)
        elif lower.endswith(".json") and "document.json" not in selected:
            selected["document.json"] = path
    normalized_dir = output_dir / "normalized"
    normalized_dir.mkdir(exist_ok=True)
    for target, source in selected.items():
        destination = normalized_dir / target
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)

    markdown_path = normalized_dir / "document.md"
    document_json = normalized_dir / "document.json"
    chunks_source = next((path for name, path in selected.items() if name.startswith("chunks.raw")), None)
    chunks = _normalize_chunks(chunks_source, source_stem) if chunks_source else []
    if not chunks and markdown_path.exists():
        chunks = _fallback_markdown_chunks(markdown_path.read_text(encoding="utf-8"), source_stem)
    _write_jsonl(normalized_dir / "chunks.jsonl", chunks)
    tables: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    if document_json.exists():
        payload = json.loads(document_json.read_text(encoding="utf-8"))
        tables, figures, formulas = _docling_visual_inventory(payload)
    _write_jsonl(normalized_dir / "tables.jsonl", tables)
    _write_jsonl(normalized_dir / "figures.jsonl", figures)
    _write_jsonl(normalized_dir / "formulas.jsonl", formulas)
    _copy_docling_assets(output_dir, normalized_dir)
    return {
        "file_count": len(files),
        "markdown_chars": len(markdown_path.read_text(encoding="utf-8")) if markdown_path.exists() else 0,
        "chunk_count": len(chunks),
        "page_grounded_chunk_count": sum(1 for chunk in chunks if chunk.get("page_start") is not None),
        "table_count": len(tables),
        "figure_count": len(figures),
        "formula_count": len(formulas),
        "normalized_dir": str(normalized_dir),
    }


def _normalize_chunks(path: Path | None, source_stem: str) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    records: list[Any]
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and isinstance(payload.get("chunks"), list):
            records = payload["chunks"]
        else:
            records = [payload]
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            record = {"text": str(record)}
        chunk_text = str(record.get("text") or record.get("content") or "").strip()
        metadata = record.get("meta") or record.get("metadata") or {}
        pages = sorted(_find_page_numbers(record))
        headings = metadata.get("headings") if isinstance(metadata, dict) else None
        if isinstance(headings, list):
            section = " > ".join(str(item) for item in headings)
        else:
            section = str((metadata.get("section") if isinstance(metadata, dict) else "") or "")
        normalized.append(
            {
                "chunk_id": "DLC_" + sha256_text(f"{source_stem}|{index}|{chunk_text}")[:20],
                "source_representation": "docling",
                "section_path": section,
                "page_start": pages[0] if pages else None,
                "page_end": pages[-1] if pages else None,
                "text": chunk_text,
                "needs_visual": _contains_visual_marker(record),
                "table_refs": [],
                "figure_refs": [],
                "citation_refs": [],
                "raw_metadata": metadata,
            }
        )
    return normalized


def _fallback_markdown_chunks(markdown: str, source_stem: str, max_chars: int = 6000) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    section = "Document"
    buffer: list[str] = []
    index = 0
    def flush() -> None:
        nonlocal index, buffer
        text = "\n".join(buffer).strip()
        if not text:
            buffer = []
            return
        for offset in range(0, len(text), max_chars):
            piece = text[offset:offset + max_chars].strip()
            if not piece:
                continue
            index += 1
            chunks.append({
                "chunk_id": "DLCF_" + sha256_text(f"{source_stem}|{index}|{piece}")[:20],
                "source_representation": "docling_markdown_fallback",
                "section_path": section,
                "page_start": None,
                "page_end": None,
                "text": piece,
                "needs_visual": "<!-- image -->" in piece or "|" in piece,
                "table_refs": [], "figure_refs": [], "citation_refs": [], "raw_metadata": {},
            })
        buffer = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            flush()
            section = line.lstrip("# ").strip() or "Document"
        else:
            buffer.append(line)
    flush()
    return chunks


def _docling_visual_inventory(
    payload: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    tables: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    seen: set[str] = set()
    def walk(value: Any, path: str = "root") -> None:
        if isinstance(value, dict):
            label = str(value.get("label") or value.get("type") or value.get("self_ref") or "").lower()
            if any(token in label for token in ("table", "picture", "figure", "formula", "equation")):
                digest = sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))[:20]
                if digest not in seen:
                    seen.add(digest)
                    row = {
                        "id": value.get("self_ref") or value.get("id") or digest,
                        "label": label,
                        "caption": _caption_text(value),
                        "provenance": value.get("prov") or value.get("provenance") or [],
                        "path": path,
                        "raw": value,
                    }
                    if "table" in label:
                        tables.append(row)
                    elif "formula" in label or "equation" in label:
                        formulas.append(row)
                    else:
                        figures.append(row)
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
    walk(payload)
    return tables, figures, formulas


def _copy_docling_assets(output_dir: Path, normalized_dir: Path) -> None:
    """Preserve referenced visual assets next to normalized HTML/Markdown exports."""
    media_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css"}
    for source in output_dir.rglob("*"):
        if not source.is_file() or normalized_dir in source.parents:
            continue
        if source.suffix.lower() not in media_suffixes:
            continue
        relative = source.relative_to(output_dir)
        destination = normalized_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)


def _caption_text(value: dict[str, Any]) -> str:
    caption = value.get("captions") or value.get("caption") or ""
    if isinstance(caption, str):
        return caption
    return json.dumps(caption, ensure_ascii=False, sort_keys=True)


def _find_page_numbers(value: Any) -> set[int]:
    result: set[int] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            lower = key.lower()
            if lower in {"page", "page_no", "page_number", "page_index"}:
                try:
                    number = int(item)
                    result.add(number + 1 if lower == "page_index" else number)
                except (TypeError, ValueError):
                    pass
            else:
                result.update(_find_page_numbers(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_find_page_numbers(item))
    return result


def _contains_visual_marker(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False, default=str).lower()
    return any(token in serialized for token in ("table", "picture", "figure", "image"))


def _build_llm_bundle(
    paper_dir: Path,
    paper_id: str,
    rank: int,
    title: str,
    pdf_source_sha256: str,
    xml_source_sha256: str,
    publisher_xml_status: str,
    docling_status: str,
    grobid_status: str,
) -> dict[str, Any]:
    llm_dir = paper_dir / "llm"
    llm_dir.mkdir(exist_ok=True)
    publisher = paper_dir / "publisher_xml"
    docling = paper_dir / "docling/normalized"
    grobid = paper_dir / "grobid/normalized"
    if publisher_xml_status == "success" and (publisher / "document.md").exists():
        text_source = publisher / "document.md"
        preferred_text_source = "publisher_xml"
    elif docling_status == "success" and (docling / "document.md").exists():
        text_source = docling / "document.md"
        preferred_text_source = "docling"
    elif grobid_status == "success" and (grobid / "document.md").exists():
        text_source = grobid / "document.md"
        preferred_text_source = "grobid"
    else:
        text_source = None
        preferred_text_source = "none"

    header = [
        "---",
        f"paper_id: {json.dumps(paper_id)}",
        f"rank: {rank}",
        f"title: {json.dumps(title)}",
        f"pdf_source_sha256: {pdf_source_sha256 or 'unknown'}",
        f"xml_source_sha256: {xml_source_sha256 or 'unknown'}",
        f"preferred_text_source: {preferred_text_source}",
        "ground_truth: original PDF or publisher XML",
        "---",
        "",
        "> Tables, figures, equations, and page-sensitive claims must be checked against the PDF/HTML/JSON representation.",
        "",
    ]
    body = text_source.read_text(encoding="utf-8") if text_source else "# No usable text representation\n"
    (llm_dir / "paper.md").write_text("\n".join(header) + body, encoding="utf-8")

    if docling_status == "success" and (docling / "chunks.jsonl").exists():
        chunks_source = docling / "chunks.jsonl"
        preferred_chunks_source = "docling"
    elif publisher_xml_status == "success" and (publisher / "chunks.jsonl").exists():
        chunks_source = publisher / "chunks.jsonl"
        preferred_chunks_source = "publisher_xml"
    elif grobid_status == "success" and (grobid / "chunks.jsonl").exists():
        chunks_source = grobid / "chunks.jsonl"
        preferred_chunks_source = "grobid"
    else:
        chunks_source = None
        preferred_chunks_source = "none"
    if chunks_source:
        shutil.copy2(chunks_source, llm_dir / "chunks.jsonl")

    reference_source = _first_existing([
        publisher / "references.jsonl",
        grobid / "references.jsonl",
    ])
    if reference_source:
        shutil.copy2(reference_source, llm_dir / "references.jsonl")
    citation_source = _first_existing([
        publisher / "citation_contexts.jsonl",
        grobid / "citation_contexts.jsonl",
    ])
    if citation_source:
        shutil.copy2(citation_source, llm_dir / "citation_contexts.jsonl")

    tables = _merge_jsonl([publisher / "tables.jsonl", docling / "tables.jsonl", grobid / "tables.jsonl"])
    figures = _merge_jsonl([publisher / "figures.jsonl", docling / "figures.jsonl", grobid / "figures.jsonl"])
    formulas = _merge_jsonl([publisher / "formulas.jsonl", docling / "formulas.jsonl", grobid / "formulas.jsonl"])
    _write_jsonl(llm_dir / "tables.jsonl", tables)
    _write_jsonl(llm_dir / "figures.jsonl", figures)
    _write_jsonl(llm_dir / "formulas.jsonl", formulas)
    return {
        "preferred_text_source": preferred_text_source,
        "preferred_chunks_source": preferred_chunks_source,
        "paper_markdown_chars": (llm_dir / "paper.md").stat().st_size,
        "chunk_count": _count_jsonl(llm_dir / "chunks.jsonl"),
        "reference_count": _count_jsonl(llm_dir / "references.jsonl"),
        "citation_context_count": _count_jsonl(llm_dir / "citation_contexts.jsonl"),
        "table_count": len(tables),
        "figure_count": len(figures),
        "formula_count": len(formulas),
        "needs_visual_review": bool(tables or figures or formulas),
    }


def _quality_assessment(
    preflight: dict[str, Any],
    publisher: dict[str, Any],
    docling: dict[str, Any],
    grobid: dict[str, Any],
    llm: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    chars = int(llm.get("paper_markdown_chars") or 0)
    chunks = int(llm.get("chunk_count") or 0)
    status = "pass"
    reasons: list[str] = []
    if chars < 1500 or chunks == 0:
        status = "fail"
        reasons.append("insufficient extracted text or chunks")
    elif warnings or preflight.get("manual_review") or llm.get("needs_visual_review"):
        status = "manual_review"
    if preflight.get("classification") in {"scanned", "hybrid"}:
        reasons.append("OCR-sensitive PDF")
    if llm.get("needs_visual_review"):
        reasons.append("tables or figures require visual verification")
    if warnings:
        reasons.extend(warnings)
    return {
        "status": status,
        "reasons": reasons,
        "preferred_text_source": llm.get("preferred_text_source"),
        "preferred_chunks_source": llm.get("preferred_chunks_source"),
        "page_grounding_available": bool(docling.get("page_grounded_chunk_count")),
        "publisher_xml_available": bool(publisher),
        "grobid_references_available": bool(grobid.get("reference_count")),
        "table_count": llm.get("table_count", 0),
        "figure_count": llm.get("figure_count", 0),
        "formula_count": llm.get("formula_count", 0),
        "manual_review_required": status == "manual_review",
    }


def _active_artifacts(settings: Settings, rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row.get("status") != "success":
            continue
        path = settings.repo / row.get("stored_path", "")
        if not path.exists():
            continue
        key = (row.get("paper_id", ""), row.get("artifact_type", ""))
        if key not in result or row.get("acquired_at", "") >= result[key].get("acquired_at", ""):
            result[key] = row
    return result


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _merge_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            digest = sha256_text(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            if digest not in seen:
                seen.add(digest)
                row["representation_source"] = path.parent.name
                result.append(row)
    return result


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def _processing_report(path: Path, manifest: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Full-text processing run",
        "",
        f"- Run: `{manifest['run_id']}`",
        f"- Papers processed: {manifest['processed_papers']}",
        "",
        "| Rank | Paper | PDF class | Publisher XML | Docling | GROBID | QA |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in rows:
        title = str(row["title"]).replace("|", "\\|")
        lines.append(
            f"| {row['rank']} | {title} | {row['preflight_class']} | {row['publisher_xml_status']} | "
            f"{row['docling_status']} | {row['grobid_status']} | {row['qa_status']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
