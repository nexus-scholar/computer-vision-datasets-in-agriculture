from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Iterable
from urllib.parse import quote

import requests

from .config import Settings
from .io_utils import redact_secrets
from .models import Candidate, Work

OPEN_LICENSE_PREFIXES = (
    "cc-by", "cc0", "public-domain", "pd", "cc-by-sa", "cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"
)


class Resolver(ABC):
    alias: str

    def __init__(self, settings: Settings, session: requests.Session):
        self.settings = settings
        self.session = session

    @abstractmethod
    def resolve(self, work: Work) -> list[Candidate]:
        raise NotImplementedError

    def get_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.get(url, timeout=self.settings.timeout_seconds, **kwargs)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


class DirectResolver(Resolver):
    alias = "direct"

    def resolve(self, work: Work) -> list[Candidate]:
        if not work.pdf_url.startswith(("http://", "https://")):
            return []
        is_pdfish = _pdfish(work.pdf_url)
        rights = "free_to_read_unknown_reuse" if work.is_open_access else "unknown"
        return [
            Candidate(
                paper_id=work.paper_id,
                source=self.alias,
                url=work.pdf_url,
                artifact_type="pdf",
                score=98 if is_pdfish else 72,
                discovery_method="screening_queue.pdf_url",
                rights_status=rights,
                is_oa=work.is_open_access,
                metadata={"direct_pdf_hint": is_pdfish},
            )
        ]


class PmcIdConverterResolver(Resolver):
    """Recover a PMCID from an exact DOI or PMID, then expose PMC/Europe PMC artifacts.

    The official PMC ID Converter is used only for identifier conversion; there is
    no title search or fuzzy matching. A contact email is required by PMC guidance.
    """

    alias = "pmc_id_converter"

    def resolve(self, work: Work) -> list[Candidate]:
        if work.pmcid or not self.settings.contact_email:
            return []
        identifier = work.pmid or work.doi
        if not identifier:
            return []
        payload = self.get_json(
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/",
            params={
                "ids": identifier,
                "format": "json",
                "tool": "AgriCVFullText",
                "email": self.settings.contact_email,
            },
        )
        records = payload.get("records") if isinstance(payload.get("records"), list) else []
        record = next((item for item in records if isinstance(item, dict) and item.get("pmcid")), None)
        if record is None:
            return []
        pmcid = str(record.get("pmcid") or "").upper()
        if not pmcid.startswith("PMC"):
            return []
        enriched = replace(work, pmcid=pmcid)
        candidates = [
            *PmcOaiResolver(self.settings, self.session).resolve(enriched),
            *EuropePmcResolver(self.settings, self.session).resolve(enriched),
        ]
        return [
            replace(
                candidate,
                discovery_method=f"pmc_id_converter({identifier})->{candidate.discovery_method}",
                metadata={
                    **candidate.metadata,
                    "pmcid": pmcid,
                    "pmid": str(record.get("pmid") or work.pmid),
                    "doi": str(record.get("doi") or work.doi),
                    "requested_id": identifier,
                },
            )
            for candidate in candidates
        ]


class PmcOaiResolver(Resolver):
    """Resolve reusable PubMed Central full text through the official OAI-PMH endpoint.

    PMC's OAI service returns full text only for records whose reuse terms permit
    inclusion in that feed. The downloaded record is still inspected for an
    explicit license before any redistribution decision is made.
    """

    alias = "pmc_oai"

    def resolve(self, work: Work) -> list[Candidate]:
        if not work.pmcid:
            return []
        numeric = re.sub(r"^PMC", "", work.pmcid.strip(), flags=re.IGNORECASE)
        if not numeric.isdigit():
            return []
        url = (
            "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/"
            f"?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{numeric}&metadataPrefix=pmc"
        )
        return [
            Candidate(
                paper_id=work.paper_id,
                source=self.alias,
                url=url,
                artifact_type="jats_xml",
                score=145,
                discovery_method="pmcid_to_pmc_oai_jats",
                license="pmc-oai-reuse-eligible-record",
                version="publishedVersion",
                host_type="repository",
                rights_status="free_to_read_unknown_reuse",
                is_oa=True,
                metadata={"pmcid": f"PMC{numeric}", "metadata_prefix": "pmc"},
            )
        ]


class EuropePmcResolver(Resolver):
    alias = "europe_pmc"

    def resolve(self, work: Work) -> list[Candidate]:
        if not work.pmcid:
            return []
        base = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        return [
            Candidate(
                paper_id=work.paper_id,
                source=self.alias,
                url=f"{base}/{work.pmcid}/fullTextXML",
                artifact_type="jats_xml",
                score=140,
                discovery_method="pmcid_to_europe_pmc_jats",
                license="repository_record",
                version="publishedVersion",
                host_type="repository",
                rights_status="free_to_read_unknown_reuse",
                is_oa=True,
            ),
            Candidate(
                paper_id=work.paper_id,
                source=self.alias,
                url=f"https://europepmc.org/articles/{work.pmcid}?pdf=render",
                artifact_type="pdf",
                score=112,
                discovery_method="pmcid_to_europe_pmc_pdf",
                license="repository_record",
                version="publishedVersion",
                host_type="repository",
                rights_status="free_to_read_unknown_reuse",
                is_oa=True,
            ),
        ]


class ArxivResolver(Resolver):
    alias = "arxiv"

    def resolve(self, work: Work) -> list[Candidate]:
        arxiv_id = work.arxiv_id.strip()
        if not arxiv_id and work.doi.lower().startswith("10.48550/arxiv."):
            arxiv_id = work.doi.split("arxiv.", 1)[1]
        if not arxiv_id:
            return []
        arxiv_id = arxiv_id.removeprefix("arXiv:").removesuffix(".pdf")
        return [
            Candidate(
                paper_id=work.paper_id,
                source=self.alias,
                url=f"https://arxiv.org/pdf/{quote(arxiv_id, safe='./')}" ,
                artifact_type="pdf",
                score=104,
                discovery_method="arxiv_id",
                license="arxiv-distribution",
                version="submittedVersion",
                host_type="repository",
                rights_status="free_to_read_unknown_reuse",
                is_oa=True,
            )
        ]


class UnpaywallResolver(Resolver):
    alias = "unpaywall"

    def resolve(self, work: Work) -> list[Candidate]:
        if not work.doi or not self.settings.unpaywall_email:
            return []
        payload = self.get_json(
            f"https://api.unpaywall.org/v2/{quote(work.doi, safe='')}",
            params={"email": self.settings.unpaywall_email},
        )
        locations = payload.get("oa_locations") or []
        best = payload.get("best_oa_location")
        if isinstance(best, dict):
            locations = [best, *[item for item in locations if item != best]]
        candidates: list[Candidate] = []
        for index, location in enumerate(locations):
            if not isinstance(location, dict):
                continue
            url = location.get("url_for_pdf") or ""
            if not url:
                continue
            license_value = str(location.get("license") or "")
            version = str(location.get("version") or "")
            host_type = str(location.get("host_type") or "")
            candidates.append(
                Candidate(
                    paper_id=work.paper_id,
                    source=self.alias,
                    url=url,
                    artifact_type="pdf",
                    score=110 - min(index, 10) + _license_bonus(license_value) + _version_bonus(version),
                    discovery_method="unpaywall.best_oa_location" if index == 0 else "unpaywall.oa_locations",
                    license=license_value,
                    version=version,
                    host_type=host_type,
                    rights_status=_rights(license_value, is_oa=True),
                    is_oa=True,
                    metadata={"oa_status": payload.get("oa_status"), "evidence": location.get("evidence")},
                )
            )
        return candidates


class CrossrefResolver(Resolver):
    alias = "crossref"

    def resolve(self, work: Work) -> list[Candidate]:
        if not work.doi:
            return []
        headers = {"User-Agent": self.settings.user_agent}
        payload = self.get_json(f"https://api.crossref.org/works/{quote(work.doi, safe='')}", headers=headers)
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        candidates: list[Candidate] = []
        for item in message.get("link") or []:
            if not isinstance(item, dict):
                continue
            content_type = str(item.get("content-type") or "").lower()
            url = str(item.get("URL") or "")
            if not url:
                continue
            if "pdf" in content_type or _pdfish(url):
                artifact_type = "pdf"
                score = 88
            elif "xml" in content_type:
                artifact_type = "xml"
                score = 101
            else:
                continue
            candidates.append(
                Candidate(
                    paper_id=work.paper_id,
                    source=self.alias,
                    url=url,
                    artifact_type=artifact_type,
                    score=score,
                    discovery_method="crossref.message.link",
                    version=str(item.get("content-version") or ""),
                    host_type="publisher",
                    rights_status="free_to_read_unknown_reuse" if work.is_open_access else "unknown",
                    is_oa=work.is_open_access,
                    metadata={"content_type": content_type, "intended_application": item.get("intended-application")},
                )
            )
        return candidates


class OpenAlexResolver(Resolver):
    alias = "openalex"

    def resolve(self, work: Work) -> list[Candidate]:
        if not self.settings.openalex_api_key:
            return []
        identifier = work.openalex_id or (f"https://doi.org/{work.doi}" if work.doi else "")
        if not identifier:
            return []
        payload = self.get_json(
            f"https://api.openalex.org/works/{quote(identifier, safe=':/')}" ,
            params={"api_key": self.settings.openalex_api_key},
        )
        locations: list[dict[str, Any]] = []
        for key in ("best_oa_location", "primary_location"):
            value = payload.get(key)
            if isinstance(value, dict):
                locations.append(value)
        locations.extend(item for item in payload.get("locations") or [] if isinstance(item, dict))
        candidates: list[Candidate] = []
        seen: set[str] = set()
        for index, location in enumerate(locations):
            url = str(location.get("pdf_url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            license_value = str(location.get("license") or "")
            version = str(location.get("version") or "")
            is_oa = bool(location.get("is_oa"))
            candidates.append(
                Candidate(
                    paper_id=work.paper_id,
                    source=self.alias,
                    url=url,
                    artifact_type="pdf",
                    score=98 - min(index, 10) + _license_bonus(license_value) + _version_bonus(version),
                    discovery_method="openalex.location.pdf_url",
                    license=license_value,
                    version=version,
                    host_type="publisher" if location.get("source", {}).get("type") == "journal" else "repository",
                    rights_status=_rights(license_value, is_oa),
                    is_oa=is_oa,
                    metadata={"openalex_work_id": payload.get("id"), "landing_page_url": location.get("landing_page_url")},
                )
            )

        work_id = str(payload.get("id") or work.openalex_id).split("/")[-1]
        best_license = ""
        if isinstance(payload.get("best_oa_location"), dict):
            best_license = str(payload["best_oa_location"].get("license") or "")
        has_content = payload.get("has_content") if isinstance(payload.get("has_content"), dict) else {}
        if self.settings.openalex_content_enabled and work_id:
            allow = bool(best_license) or self.settings.openalex_content_allow_unknown_license
            if allow and has_content.get("grobid_xml"):
                candidates.append(
                    Candidate(
                        paper_id=work.paper_id,
                        source="openalex_content",
                        url=f"https://content.openalex.org/works/{work_id}.grobid-xml",
                        artifact_type="tei_xml",
                        score=118 + _license_bonus(best_license),
                        discovery_method="openalex.content_url",
                        license=best_license,
                        rights_status=_rights(best_license, bool(best_license)),
                        is_oa=bool(best_license),
                        expected_cost_usd=0.01,
                        metadata={"openalex_work_id": work_id},
                    )
                )
            if allow and has_content.get("pdf"):
                candidates.append(
                    Candidate(
                        paper_id=work.paper_id,
                        source="openalex_content",
                        url=f"https://content.openalex.org/works/{work_id}.pdf",
                        artifact_type="pdf",
                        score=92 + _license_bonus(best_license),
                        discovery_method="openalex.content_url",
                        license=best_license,
                        rights_status=_rights(best_license, bool(best_license)),
                        is_oa=bool(best_license),
                        expected_cost_usd=0.01,
                        metadata={"openalex_work_id": work_id},
                    )
                )
        return candidates


class SemanticScholarResolver(Resolver):
    alias = "semantic_scholar"

    def resolve(self, work: Work) -> list[Candidate]:
        identifier = work.semantic_scholar_id or (f"DOI:{work.doi}" if work.doi else "")
        if not identifier:
            return []
        headers = {"x-api-key": self.settings.semantic_scholar_api_key} if self.settings.semantic_scholar_api_key else {}
        try:
            payload = self.get_json(
                f"https://api.semanticscholar.org/graph/v1/paper/{quote(identifier, safe=':')}" ,
                params={"fields": "paperId,title,externalIds,openAccessPdf,url,year"},
                headers=headers,
            )
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in {404, 429}:
                return []
            raise
        oa = payload.get("openAccessPdf") if isinstance(payload.get("openAccessPdf"), dict) else {}
        url = str(oa.get("url") or "")
        if not url:
            return []
        license_value = str(oa.get("license") or "")
        return [
            Candidate(
                paper_id=work.paper_id,
                source=self.alias,
                url=url,
                artifact_type="pdf",
                score=94 + _license_bonus(license_value),
                discovery_method="semantic_scholar.openAccessPdf",
                license=license_value,
                rights_status=_rights(license_value, True),
                is_oa=True,
                metadata={"semantic_scholar_id": payload.get("paperId"), "status": oa.get("status")},
            )
        ]


def build_resolvers(settings: Settings, session: requests.Session) -> list[Resolver]:
    factories: dict[str, type[Resolver]] = {
        "direct": DirectResolver,
        "pmc_id_converter": PmcIdConverterResolver,
        "pmc_oai": PmcOaiResolver,
        "europe_pmc": EuropePmcResolver,
        "arxiv": ArxivResolver,
        "unpaywall": UnpaywallResolver,
        "crossref": CrossrefResolver,
        "openalex": OpenAlexResolver,
        "semantic_scholar": SemanticScholarResolver,
    }
    return [factories[name](settings, session) for name in settings.source_order if name in factories]


def resolve_candidates(settings: Settings, work: Work, session: requests.Session) -> tuple[list[Candidate], list[dict[str, str]]]:
    candidates: list[Candidate] = []
    errors: list[dict[str, str]] = []
    for resolver in build_resolvers(settings, session):
        try:
            candidates.extend(resolver.resolve(work))
        except Exception as exc:  # source failures should not abort the whole work
            errors.append({"paper_id": work.paper_id, "source": resolver.alias, "error": redact_secrets(f"{type(exc).__name__}: {exc}", [settings.openalex_api_key, settings.semantic_scholar_api_key, settings.unpaywall_email])})
    deduped: dict[tuple[str, str], Candidate] = {}
    for candidate in candidates:
        key = (candidate.artifact_type, _normalize_url(candidate.url))
        current = deduped.get(key)
        if current is None or candidate.score > current.score:
            deduped[key] = candidate
    return sorted(deduped.values(), key=lambda item: (-item.score, item.expected_cost_usd, item.source)), errors


def auto_download_allowed(candidate: Candidate, settings: Settings) -> bool:
    if candidate.rights_status in {"open_license", "free_to_read_unknown_reuse"}:
        return True
    return settings.allow_unknown_rights


def _pdfish(url: str) -> bool:
    lower = url.lower().split("#", 1)[0]
    return lower.endswith(".pdf") or "/pdf" in lower or "pdf=" in lower


def _normalize_url(url: str) -> str:
    return re.sub(r"([?&])api_key=[^&]+", r"\1api_key=REDACTED", url.strip())


def _license_bonus(value: str) -> int:
    return 12 if _open_license(value) else (3 if value else 0)


def _version_bonus(value: str) -> int:
    normalized = value.lower()
    if "published" in normalized:
        return 12
    if "accepted" in normalized:
        return 7
    if "submitted" in normalized:
        return 3
    return 0


def _open_license(value: str) -> bool:
    normalized = value.strip().lower().replace("_", "-")
    return normalized.startswith(OPEN_LICENSE_PREFIXES)


def _rights(license_value: str, is_oa: bool) -> str:
    if _open_license(license_value):
        return "open_license"
    if is_oa:
        return "free_to_read_unknown_reuse"
    return "unknown"
