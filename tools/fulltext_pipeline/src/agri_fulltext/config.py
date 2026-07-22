from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    repo: Path
    queue_path: Path
    decisions_path: Path
    raw_dir: Path
    artifact_registry: Path
    attempt_registry: Path
    resolver_error_registry: Path
    extraction_registry: Path
    quality_reviews: Path
    output_root: Path
    processing_root: Path
    user_agent: str
    timeout_seconds: int = 45
    max_retries: int = 2
    max_bytes: int = 100_000_000
    failed_cooldown_hours: int = 24
    source_order: tuple[str, ...] = (
        "direct",
        "pmc_id_converter",
        "pmc_oai",
        "europe_pmc",
        "arxiv",
        "unpaywall",
        "crossref",
        "openalex",
        "semantic_scholar",
    )
    contact_email: str = ""
    unpaywall_email: str = ""
    openalex_api_key: str = ""
    semantic_scholar_api_key: str = ""
    openalex_content_enabled: bool = False
    openalex_content_allow_unknown_license: bool = False
    allow_unknown_rights: bool = False
    grobid_url: str = "http://localhost:8070"
    docling_mode: str = "local"
    docling_service_url: str = ""
    docling_device: str = "auto"
    docling_threads: int = 4
    docling_timeout_seconds: int = 900
    config_payload: dict[str, Any] = field(default_factory=dict, compare=False)


def load_settings(repo: Path, config_path: Path | None = None) -> Settings:
    repo = repo.resolve()
    config_path = (config_path or (repo / "config/fulltext.toml")).resolve()
    data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)

    project = data.get("project", {})
    acquisition = data.get("acquisition", {})
    processing = data.get("processing", {})

    def p(value: str, default: str) -> Path:
        return (repo / str(value or default)).resolve()

    source_order = tuple(acquisition.get("source_order", [])) or Settings.__dataclass_fields__["source_order"].default
    return Settings(
        repo=repo,
        queue_path=p(project.get("queue_path", ""), "outputs/screening_queue_2026-07-22/screening_queue.csv"),
        decisions_path=p(
            project.get("decisions_path", ""),
            "data/curated/screening/title_abstract_decisions_enriched.csv",
        ),
        raw_dir=p(project.get("raw_dir", ""), "data/raw/fulltext"),
        artifact_registry=p(
            project.get("artifact_registry", ""),
            "data/curated/fulltext/artifact_registry.csv",
        ),
        attempt_registry=p(
            project.get("attempt_registry", ""),
            "data/curated/fulltext/fetch_attempt_registry.csv",
        ),
        resolver_error_registry=p(
            project.get("resolver_error_registry", ""),
            "data/curated/fulltext/resolver_error_registry.csv",
        ),
        extraction_registry=p(
            project.get("extraction_registry", ""),
            "data/curated/fulltext/extraction_registry.csv",
        ),
        quality_reviews=p(
            project.get("quality_reviews", ""),
            "data/curated/fulltext/fulltext_quality_reviews.csv",
        ),
        output_root=p(project.get("output_root", ""), "outputs/fulltext/acquisition"),
        processing_root=p(project.get("processing_root", ""), "outputs/fulltext/processing"),
        user_agent=str(
            os.getenv("FULLTEXT_USER_AGENT")
            or acquisition.get("user_agent")
            or "AgriCVFullText/0.1 (academic review; contact configured separately)"
        ),
        timeout_seconds=int(acquisition.get("timeout_seconds", 45)),
        max_retries=int(acquisition.get("max_retries", 2)),
        max_bytes=int(acquisition.get("max_bytes", 100_000_000)),
        failed_cooldown_hours=int(acquisition.get("failed_cooldown_hours", 24)),
        source_order=source_order,
        contact_email=str(
            os.getenv("FULLTEXT_CONTACT_EMAIL")
            or acquisition.get("contact_email")
            or os.getenv("UNPAYWALL_EMAIL")
            or acquisition.get("unpaywall_email")
            or ""
        ),
        unpaywall_email=str(os.getenv("UNPAYWALL_EMAIL") or acquisition.get("unpaywall_email") or ""),
        openalex_api_key=str(os.getenv("OPENALEX_API_KEY") or acquisition.get("openalex_api_key") or ""),
        semantic_scholar_api_key=str(
            os.getenv("S2_API_KEY") or acquisition.get("semantic_scholar_api_key") or ""
        ),
        openalex_content_enabled=_bool(
            os.getenv("OPENALEX_CONTENT_ENABLED"), acquisition.get("openalex_content_enabled", False)
        ),
        openalex_content_allow_unknown_license=_bool(
            os.getenv("OPENALEX_CONTENT_ALLOW_UNKNOWN_LICENSE"),
            acquisition.get("openalex_content_allow_unknown_license", False),
        ),
        allow_unknown_rights=_bool(
            os.getenv("FULLTEXT_ALLOW_UNKNOWN_RIGHTS"), acquisition.get("allow_unknown_rights", False)
        ),
        grobid_url=str(os.getenv("GROBID_URL") or processing.get("grobid_url") or "http://localhost:8070"),
        docling_mode=str(os.getenv("DOCLING_MODE") or processing.get("docling_mode") or "local"),
        docling_service_url=str(
            os.getenv("DOCLING_SERVICE_URL") or processing.get("docling_service_url") or ""
        ),
        docling_device=str(os.getenv("DOCLING_DEVICE") or processing.get("docling_device") or "auto"),
        docling_threads=int(processing.get("docling_threads", 4)),
        docling_timeout_seconds=int(processing.get("docling_timeout_seconds", 900)),
        config_payload=data,
    )


def _bool(env_value: str | None, default: Any) -> bool:
    if env_value is None:
        return bool(default)
    return env_value.strip().lower() in {"1", "true", "yes", "on"}
