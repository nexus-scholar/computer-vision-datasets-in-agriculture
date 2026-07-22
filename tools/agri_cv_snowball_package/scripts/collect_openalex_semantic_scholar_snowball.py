#!/usr/bin/env python3
"""
Collect one-hop backward and forward snowballing metadata for seed papers using
OpenAlex and Semantic Scholar Graph API.

Inputs:
  input/seed_papers_manifest.csv  (created from the 13 curated agriculture CV papers)

Outputs:
  seed_papers_provider_metadata.csv
  seed_papers_merged_metadata.csv
  backward_references.csv
  forward_citations.csv
  snowball_edges.csv
  snowball_nodes.csv
  run_summary.csv
  unresolved_seeds.csv
  cache/*.json

Notes:
- This script uses legal public scholarly metadata APIs only.
- Semantic Scholar has tighter unauthenticated rate limits. Set S2_API_KEY when available.
- Default snowball depth is 1: references used by each seed and papers citing each seed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests
except ImportError as exc:
    raise SystemExit("Missing dependency: requests. Install with: pip install requests") from exc

OPENALEX_BASE = "https://api.openalex.org"
S2_BASE = "https://api.semanticscholar.org/graph/v1"

S2_PAPER_FIELDS = ",".join([
    "paperId", "corpusId", "url", "title", "abstract", "venue", "year",
    "publicationDate", "publicationTypes", "publicationVenue", "journal",
    "authors", "externalIds", "referenceCount", "citationCount",
    "influentialCitationCount", "isOpenAccess", "openAccessPdf",
    "fieldsOfStudy", "s2FieldsOfStudy",
])

S2_REF_FIELDS = ",".join([
    "contexts", "intents", "isInfluential",
    "citedPaper.paperId", "citedPaper.corpusId", "citedPaper.url", "citedPaper.title",
    "citedPaper.abstract", "citedPaper.venue", "citedPaper.year", "citedPaper.publicationDate",
    "citedPaper.publicationTypes", "citedPaper.publicationVenue", "citedPaper.journal",
    "citedPaper.authors", "citedPaper.externalIds", "citedPaper.referenceCount",
    "citedPaper.citationCount", "citedPaper.influentialCitationCount", "citedPaper.isOpenAccess",
    "citedPaper.openAccessPdf", "citedPaper.fieldsOfStudy", "citedPaper.s2FieldsOfStudy",
])

S2_CIT_FIELDS = ",".join([
    "contexts", "intents", "isInfluential",
    "citingPaper.paperId", "citingPaper.corpusId", "citingPaper.url", "citingPaper.title",
    "citingPaper.abstract", "citingPaper.venue", "citingPaper.year", "citingPaper.publicationDate",
    "citingPaper.publicationTypes", "citingPaper.publicationVenue", "citingPaper.journal",
    "citingPaper.authors", "citingPaper.externalIds", "citingPaper.referenceCount",
    "citingPaper.citationCount", "citingPaper.influentialCitationCount", "citingPaper.isOpenAccess",
    "citingPaper.openAccessPdf", "citingPaper.fieldsOfStudy", "citingPaper.s2FieldsOfStudy",
])

SEED_PROVIDER_COLUMNS = [
    "seed_row_id", "dataset_name", "provider", "match_status", "match_method", "match_score",
    "provider_work_id", "openalex_id", "semantic_scholar_paper_id", "corpus_id", "doi", "arxiv_id", "pmid", "pmcid",
    "title", "year", "publication_date", "type", "venue", "journal", "authors", "url",
    "landing_page_url", "pdf_url", "is_open_access", "open_access_status", "citation_count",
    "reference_count", "influential_citation_count", "is_retracted", "language", "topics_or_fields",
    "abstract", "source_input_title", "source_input_doi", "source_primary_url", "raw_json_path",
]

EDGE_COLUMNS = [
    "seed_row_id", "dataset_name", "direction", "provider", "seed_provider_work_id", "edge_index",
    "source_provider_work_id", "source_title", "source_year", "source_doi", "source_url",
    "target_provider_work_id", "target_title", "target_year", "target_doi", "target_url",
    "related_provider_work_id", "related_title", "related_year", "related_publication_date", "related_type",
    "related_venue", "related_journal", "related_authors", "related_doi", "related_arxiv_id",
    "related_pmid", "related_pmcid", "related_url", "related_pdf_url", "related_is_open_access",
    "related_citation_count", "related_reference_count", "related_influential_citation_count",
    "contexts", "intents", "is_influential", "abstract", "node_key",
]

NODE_COLUMNS = [
    "node_key", "provider", "provider_work_id", "openalex_id", "semantic_scholar_paper_id", "corpus_id",
    "doi", "arxiv_id", "pmid", "pmcid", "title", "year", "publication_date", "type", "venue", "journal",
    "authors", "url", "pdf_url", "is_open_access", "citation_count", "reference_count",
    "influential_citation_count", "source_roles", "seen_from_seed_ids", "abstract",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def normalize_title(title: str) -> str:
    title = (title or "").lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def title_score(a: str, b: str) -> float:
    aa, bb = normalize_title(a), normalize_title(b)
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 1.0
    return SequenceMatcher(None, aa, bb).ratio()


def clean_doi(doi: str) -> str:
    doi = (doi or "").strip().lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    doi = doi.strip().strip(".;,)")
    return doi


def split_authors_openalex(authorships: List[Dict[str, Any]]) -> str:
    names = []
    for a in authorships or []:
        author = a.get("author") or {}
        name = author.get("display_name")
        if name:
            names.append(name)
    return "; ".join(names)


def split_authors_s2(authors: List[Dict[str, Any]]) -> str:
    return "; ".join([a.get("name", "") for a in (authors or []) if a.get("name")])


def inverted_abstract_to_text(inv: Optional[Dict[str, List[int]]]) -> str:
    if not inv:
        return ""
    positions = []
    for word, idxs in inv.items():
        for idx in idxs:
            positions.append((idx, word))
    return " ".join(word for _, word in sorted(positions))


def get_nested(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def external_id(external: Optional[Dict[str, Any]], key: str) -> str:
    if not external:
        return ""
    for k, v in external.items():
        if k.lower() == key.lower():
            return str(v)
    return ""


def oa_primary_source(work: Dict[str, Any]) -> Tuple[str, str]:
    loc = work.get("primary_location") or {}
    source = loc.get("source") or {}
    return source.get("display_name", ""), source.get("host_organization_name", "") or ""


def oa_pdf_url(work: Dict[str, Any]) -> str:
    best = work.get("best_oa_location") or {}
    loc = work.get("primary_location") or {}
    return best.get("pdf_url") or loc.get("pdf_url") or ""


def oa_landing_url(work: Dict[str, Any]) -> str:
    loc = work.get("primary_location") or {}
    return (loc.get("landing_page_url") or work.get("doi") or work.get("id") or "")


def oa_topics(work: Dict[str, Any]) -> str:
    topics = []
    for t in work.get("topics") or []:
        name = t.get("display_name") or t.get("id")
        if name:
            topics.append(name)
    if not topics:
        for c in work.get("concepts") or []:
            name = c.get("display_name")
            if name:
                topics.append(name)
    return "; ".join(topics[:20])


def s2_topics(paper: Dict[str, Any]) -> str:
    topics = []
    for f in paper.get("s2FieldsOfStudy") or []:
        if isinstance(f, dict) and f.get("category"):
            topics.append(f["category"])
    for f in paper.get("fieldsOfStudy") or []:
        if f:
            topics.append(str(f))
    # stable unique preserving order
    seen = set(); out = []
    for t in topics:
        if t not in seen:
            out.append(t); seen.add(t)
    return "; ".join(out)


def s2_pdf_url(paper: Dict[str, Any]) -> str:
    pdf = paper.get("openAccessPdf") or {}
    return pdf.get("url") or ""


def s2_journal(paper: Dict[str, Any]) -> str:
    j = paper.get("journal") or {}
    if isinstance(j, dict):
        parts = [j.get("name") or "", j.get("volume") or "", j.get("pages") or ""]
        return ", ".join([p for p in parts if p])
    return ""


def s2_venue(paper: Dict[str, Any]) -> str:
    venue = paper.get("venue") or ""
    pv = paper.get("publicationVenue") or {}
    if isinstance(pv, dict) and pv.get("name") and pv.get("name") not in venue:
        return pv.get("name")
    return venue


def node_key_from(provider: str, item: Dict[str, Any], doi: str = "", title: str = "", year: Any = "") -> str:
    doi = clean_doi(doi or item.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    if provider == "openalex" and (item.get("openalex_id") or item.get("id")):
        return f"openalex:{str(item.get('openalex_id') or item.get('id')).rsplit('/', 1)[-1]}"
    if provider == "semantic_scholar" and (item.get("paperId") or item.get("semantic_scholar_paper_id")):
        return f"s2:{item.get('paperId') or item.get('semantic_scholar_paper_id')}"
    nt = normalize_title(title or item.get("title", ""))
    return f"titleyear:{nt[:120]}:{year or item.get('year','')}"


@dataclass
class ClientConfig:
    mailto: str = ""
    openalex_api_key: str = ""
    s2_api_key: str = ""
    min_title_score: float = 0.88
    cache_dir: Path = Path("cache")
    openalex_sleep: float = 0.12
    s2_sleep: float = 1.2
    retries: int = 4
    timeout: int = 40
    refresh_cache: bool = False


class CachedHttpClient:
    def __init__(self, config: ClientConfig):
        self.config = config
        self.cache_dir = config.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, url: str, params: Optional[Dict[str, Any]]) -> Path:
        key = url + "?" + urllib.parse.urlencode(sorted((params or {}).items()), doseq=True)
        return self.cache_dir / (hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json")

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
                 sleep_after: float = 0.0) -> Tuple[Optional[Dict[str, Any]], str, str]:
        params = dict(params or {})
        cache_path = self._cache_path(url, params)
        if cache_path.exists() and not self.config.refresh_cache:
            try:
                return json.loads(cache_path.read_text(encoding="utf-8")), "cache", str(cache_path)
            except Exception:
                pass

        last_error = ""
        for attempt in range(self.config.retries):
            try:
                resp = requests.get(url, params=params, headers=headers or {}, timeout=self.config.timeout)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.replace('.', '', 1).isdigit() else (2 ** attempt) * max(1.0, sleep_after)
                    print(f"[rate-limit] {url} sleeping {delay:.1f}s", file=sys.stderr)
                    time.sleep(delay)
                    continue
                if resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    time.sleep((2 ** attempt) * 1.5)
                    continue
                if resp.status_code == 404:
                    return None, "404", str(cache_path)
                if resp.status_code >= 400:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                    return None, last_error, str(cache_path)
                data = resp.json()
                cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                if sleep_after:
                    time.sleep(sleep_after)
                return data, "live", str(cache_path)
            except Exception as exc:
                last_error = repr(exc)
                time.sleep((2 ** attempt) * 1.5)
        return None, last_error, str(cache_path)


class OpenAlexClient:
    def __init__(self, http: CachedHttpClient, config: ClientConfig):
        self.http = http
        self.config = config

    def _params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = dict(extra or {})
        if self.config.mailto:
            params["mailto"] = self.config.mailto
        if self.config.openalex_api_key:
            params["api_key"] = self.config.openalex_api_key
        return params

    def get_work_by_identifier(self, identifier: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
        # Identifier can be W..., DOI URL, doi:..., pmid:..., pmcid:...
        quoted = urllib.parse.quote(identifier, safe="")
        url = f"{OPENALEX_BASE}/works/{quoted}"
        return self.http.get_json(url, self._params(), sleep_after=self.config.openalex_sleep)

    def search_work(self, title: str, year_hint: str = "") -> Tuple[Optional[Dict[str, Any]], str, float, str]:
        params = self._params({"search": title, "per-page": 10})
        data, status, cache_path = self.http.get_json(f"{OPENALEX_BASE}/works", params, sleep_after=self.config.openalex_sleep)
        if not data or not data.get("results"):
            return None, f"search_failed:{status}", 0.0, cache_path
        best = None; best_score = 0.0
        for item in data.get("results", []):
            score = title_score(title, item.get("title", ""))
            if year_hint and str(item.get("publication_year", "")) and str(year_hint).split("/")[0] in str(item.get("publication_year", "")):
                score += 0.03
            if score > best_score:
                best = item; best_score = score
        if best and best_score >= self.config.min_title_score:
            return best, "search_title", min(best_score, 1.0), cache_path
        return best, "low_confidence_search_title", best_score, cache_path

    def resolve_seed(self, seed: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], str, float, str, str]:
        attempts = []
        doi = clean_doi(seed.get("doi", ""))
        if doi:
            attempts.extend([f"https://doi.org/{doi}", f"doi:{doi}"])
        if seed.get("pmid"):
            attempts.append(f"pmid:{seed['pmid']}")
        if seed.get("pmcid"):
            attempts.append(f"pmcid:{seed['pmcid']}")
        for ident in attempts:
            work, status, cache_path = self.get_work_by_identifier(ident)
            if work and work.get("id"):
                return work, f"identifier:{ident}", 1.0, status, cache_path
        work, method, score, cache_path = self.search_work(seed.get("title", ""), seed.get("year_hint", ""))
        if work and method == "search_title":
            return work, method, score, "live_or_cache", cache_path
        if work:
            return work, method, score, "low_confidence", cache_path
        return None, "unresolved", 0.0, "", cache_path

    def fetch_work(self, openalex_id: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
        ident = openalex_id.rsplit("/", 1)[-1]
        return self.get_work_by_identifier(ident)

    def iter_cited_by(self, work: Dict[str, Any], max_records: int = 0) -> Iterable[Dict[str, Any]]:
        # Prefer cited_by_api_url if present; fall back to works?filter=cites:<WID>
        api_url = work.get("cited_by_api_url")
        if not api_url:
            wid = (work.get("id") or "").rsplit("/", 1)[-1]
            api_url = f"{OPENALEX_BASE}/works?filter=cites:{wid}"
        cursor = "*"
        yielded = 0
        while True:
            # The cited_by_api_url already includes query params. Parse and merge cursor/per-page/mailto.
            parsed = urllib.parse.urlparse(api_url)
            base = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
            query = dict(urllib.parse.parse_qsl(parsed.query))
            query.update({"per-page": "200", "cursor": cursor})
            if self.config.mailto:
                query["mailto"] = self.config.mailto
            if self.config.openalex_api_key:
                query["api_key"] = self.config.openalex_api_key
            data, status, _ = self.http.get_json(base, query, sleep_after=self.config.openalex_sleep)
            if not data or not data.get("results"):
                break
            for item in data.get("results", []):
                yield item
                yielded += 1
                if max_records and yielded >= max_records:
                    return
            next_cursor = (data.get("meta") or {}).get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor


class SemanticScholarClient:
    def __init__(self, http: CachedHttpClient, config: ClientConfig):
        self.http = http
        self.config = config
        self.relation_errors: List[Dict[str, str]] = []

    def _headers(self) -> Dict[str, str]:
        if self.config.s2_api_key:
            return {"x-api-key": self.config.s2_api_key}
        return {}

    def get_paper(self, paper_identifier: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
        quoted = urllib.parse.quote(paper_identifier, safe="")
        url = f"{S2_BASE}/paper/{quoted}"
        return self.http.get_json(url, {"fields": S2_PAPER_FIELDS}, headers=self._headers(), sleep_after=self.config.s2_sleep)

    def search_work(self, title: str, year_hint: str = "") -> Tuple[Optional[Dict[str, Any]], str, float, str]:
        params = {"query": title, "limit": 10, "fields": S2_PAPER_FIELDS}
        data, status, cache_path = self.http.get_json(f"{S2_BASE}/paper/search", params, headers=self._headers(), sleep_after=self.config.s2_sleep)
        if not data or not data.get("data"):
            return None, f"search_failed:{status}", 0.0, cache_path
        best = None; best_score = 0.0
        for item in data.get("data", []):
            score = title_score(title, item.get("title", ""))
            if year_hint and str(item.get("year", "")) and str(year_hint).split("/")[0] in str(item.get("year", "")):
                score += 0.03
            if score > best_score:
                best = item; best_score = score
        if best and best_score >= self.config.min_title_score:
            return best, "search_title", min(best_score, 1.0), cache_path
        return best, "low_confidence_search_title", best_score, cache_path

    def resolve_seed(self, seed: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], str, float, str, str]:
        attempts = []
        doi = clean_doi(seed.get("doi", ""))
        if doi:
            attempts.append(f"DOI:{doi}")
        if seed.get("arxiv_id"):
            attempts.append(f"ARXIV:{seed['arxiv_id']}")
        if seed.get("pmid"):
            attempts.append(f"PMID:{seed['pmid']}")
        if seed.get("pmcid"):
            attempts.append(f"PMCID:{seed['pmcid']}")
        for ident in attempts:
            paper, status, cache_path = self.get_paper(ident)
            if paper and paper.get("paperId"):
                return paper, f"identifier:{ident}", 1.0, status, cache_path
        paper, method, score, cache_path = self.search_work(seed.get("title", ""), seed.get("year_hint", ""))
        if paper and method == "search_title":
            return paper, method, score, "live_or_cache", cache_path
        if paper:
            return paper, method, score, "low_confidence", cache_path
        return None, "unresolved", 0.0, "", cache_path

    def iter_relations(self, paper_id: str, relation: str, max_records: int = 0) -> Iterable[Dict[str, Any]]:
        assert relation in {"references", "citations"}
        fields = S2_REF_FIELDS if relation == "references" else S2_CIT_FIELDS
        offset = 0
        limit = 1000
        yielded = 0
        while True:
            url = f"{S2_BASE}/paper/{urllib.parse.quote(paper_id, safe='')}/{relation}"
            params = {"fields": fields, "limit": limit, "offset": offset}
            data, status, cache_path = self.http.get_json(url, params, headers=self._headers(), sleep_after=self.config.s2_sleep)
            if data is None:
                self.relation_errors.append({
                    "paper_id": paper_id, "relation": relation, "offset": str(offset),
                    "status": status, "cache_path": cache_path,
                })
                break
            if not data.get("data"):
                break
            batch = data.get("data", [])
            for item in batch:
                yield item
                yielded += 1
                if max_records and yielded >= max_records:
                    return
            if len(batch) < limit:
                break
            offset += len(batch)


def openalex_to_row(seed: Dict[str, str], work: Dict[str, Any], match_status: str, method: str, score: float, raw_path: str) -> Dict[str, str]:
    venue, journal = oa_primary_source(work)
    ids = work.get("ids") or {}
    doi = clean_doi((work.get("doi") or ids.get("doi") or "").replace("https://doi.org/", ""))
    oa = work.get("open_access") or {}
    row = {
        "seed_row_id": seed.get("row_id", ""),
        "dataset_name": seed.get("dataset_name", ""),
        "provider": "openalex",
        "match_status": match_status,
        "match_method": method,
        "match_score": f"{score:.4f}",
        "provider_work_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "openalex_id": work.get("id", ""),
        "semantic_scholar_paper_id": "",
        "corpus_id": "",
        "doi": doi,
        "arxiv_id": "",
        "pmid": str(ids.get("pmid", "")).replace("https://pubmed.ncbi.nlm.nih.gov/", ""),
        "pmcid": str(ids.get("pmcid", "")).rsplit("/", 1)[-1] if ids.get("pmcid") else "",
        "title": work.get("title", ""),
        "year": work.get("publication_year", ""),
        "publication_date": work.get("publication_date", ""),
        "type": work.get("type", ""),
        "venue": venue,
        "journal": journal,
        "authors": split_authors_openalex(work.get("authorships") or []),
        "url": oa_landing_url(work),
        "landing_page_url": oa_landing_url(work),
        "pdf_url": oa_pdf_url(work),
        "is_open_access": safe_str(oa.get("is_oa", "")),
        "open_access_status": oa.get("oa_status", ""),
        "citation_count": work.get("cited_by_count", ""),
        "reference_count": len(work.get("referenced_works") or []),
        "influential_citation_count": "",
        "is_retracted": safe_str(work.get("is_retracted", "")),
        "language": work.get("language", ""),
        "topics_or_fields": oa_topics(work),
        "abstract": inverted_abstract_to_text(work.get("abstract_inverted_index")),
        "source_input_title": seed.get("title", ""),
        "source_input_doi": seed.get("doi", ""),
        "source_primary_url": seed.get("primary_url", ""),
        "raw_json_path": raw_path,
    }
    return {k: safe_str(row.get(k, "")) for k in SEED_PROVIDER_COLUMNS}


def s2_to_row(seed: Dict[str, str], paper: Dict[str, Any], match_status: str, method: str, score: float, raw_path: str) -> Dict[str, str]:
    ext = paper.get("externalIds") or {}
    doi = clean_doi(external_id(ext, "DOI"))
    row = {
        "seed_row_id": seed.get("row_id", ""),
        "dataset_name": seed.get("dataset_name", ""),
        "provider": "semantic_scholar",
        "match_status": match_status,
        "match_method": method,
        "match_score": f"{score:.4f}",
        "provider_work_id": paper.get("paperId", ""),
        "openalex_id": external_id(ext, "OpenAlex"),
        "semantic_scholar_paper_id": paper.get("paperId", ""),
        "corpus_id": paper.get("corpusId", ""),
        "doi": doi,
        "arxiv_id": external_id(ext, "ArXiv"),
        "pmid": external_id(ext, "PubMed"),
        "pmcid": external_id(ext, "PubMedCentral") or external_id(ext, "PMCID"),
        "title": paper.get("title", ""),
        "year": paper.get("year", ""),
        "publication_date": paper.get("publicationDate", ""),
        "type": "; ".join(paper.get("publicationTypes") or []),
        "venue": s2_venue(paper),
        "journal": s2_journal(paper),
        "authors": split_authors_s2(paper.get("authors") or []),
        "url": paper.get("url", ""),
        "landing_page_url": paper.get("url", ""),
        "pdf_url": s2_pdf_url(paper),
        "is_open_access": safe_str(paper.get("isOpenAccess", "")),
        "open_access_status": "",
        "citation_count": paper.get("citationCount", ""),
        "reference_count": paper.get("referenceCount", ""),
        "influential_citation_count": paper.get("influentialCitationCount", ""),
        "is_retracted": "",
        "language": "",
        "topics_or_fields": s2_topics(paper),
        "abstract": paper.get("abstract", ""),
        "source_input_title": seed.get("title", ""),
        "source_input_doi": seed.get("doi", ""),
        "source_primary_url": seed.get("primary_url", ""),
        "raw_json_path": raw_path,
    }
    return {k: safe_str(row.get(k, "")) for k in SEED_PROVIDER_COLUMNS}


def openalex_related_to_flat(work: Dict[str, Any]) -> Dict[str, Any]:
    ids = work.get("ids") or {}
    venue, journal = oa_primary_source(work)
    doi = clean_doi((work.get("doi") or ids.get("doi") or "").replace("https://doi.org/", ""))
    oa = work.get("open_access") or {}
    return {
        "provider_work_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "openalex_id": work.get("id", ""),
        "semantic_scholar_paper_id": "",
        "corpus_id": "",
        "doi": doi,
        "arxiv_id": "",
        "pmid": str(ids.get("pmid", "")).replace("https://pubmed.ncbi.nlm.nih.gov/", ""),
        "pmcid": str(ids.get("pmcid", "")).rsplit("/", 1)[-1] if ids.get("pmcid") else "",
        "title": work.get("title", ""),
        "year": work.get("publication_year", ""),
        "publication_date": work.get("publication_date", ""),
        "type": work.get("type", ""),
        "venue": venue,
        "journal": journal,
        "authors": split_authors_openalex(work.get("authorships") or []),
        "url": oa_landing_url(work),
        "pdf_url": oa_pdf_url(work),
        "is_open_access": oa.get("is_oa", ""),
        "citation_count": work.get("cited_by_count", ""),
        "reference_count": len(work.get("referenced_works") or []),
        "influential_citation_count": "",
        "abstract": inverted_abstract_to_text(work.get("abstract_inverted_index")),
    }


def s2_related_to_flat(paper: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    paper = paper or {}
    ext = paper.get("externalIds") or {}
    return {
        "provider_work_id": paper.get("paperId", ""),
        "openalex_id": external_id(ext, "OpenAlex"),
        "semantic_scholar_paper_id": paper.get("paperId", ""),
        "corpus_id": paper.get("corpusId", ""),
        "doi": clean_doi(external_id(ext, "DOI")),
        "arxiv_id": external_id(ext, "ArXiv"),
        "pmid": external_id(ext, "PubMed"),
        "pmcid": external_id(ext, "PubMedCentral") or external_id(ext, "PMCID"),
        "title": paper.get("title", ""),
        "year": paper.get("year", ""),
        "publication_date": paper.get("publicationDate", ""),
        "type": "; ".join(paper.get("publicationTypes") or []),
        "venue": s2_venue(paper),
        "journal": s2_journal(paper),
        "authors": split_authors_s2(paper.get("authors") or []),
        "url": paper.get("url", ""),
        "pdf_url": s2_pdf_url(paper),
        "is_open_access": paper.get("isOpenAccess", ""),
        "citation_count": paper.get("citationCount", ""),
        "reference_count": paper.get("referenceCount", ""),
        "influential_citation_count": paper.get("influentialCitationCount", ""),
        "abstract": paper.get("abstract", ""),
    }


def make_edge(seed: Dict[str, str], provider: str, direction: str, seed_flat: Dict[str, Any], related_flat: Dict[str, Any],
              edge_index: int, contexts: Any = "", intents: Any = "", is_influential: Any = "") -> Dict[str, str]:
    if direction == "backward_reference":
        source = seed_flat
        target = related_flat
    else:
        source = related_flat
        target = seed_flat
    row = {
        "seed_row_id": seed.get("row_id", ""),
        "dataset_name": seed.get("dataset_name", ""),
        "direction": direction,
        "provider": provider,
        "seed_provider_work_id": seed_flat.get("provider_work_id", ""),
        "edge_index": edge_index,
        "source_provider_work_id": source.get("provider_work_id", ""),
        "source_title": source.get("title", ""),
        "source_year": source.get("year", ""),
        "source_doi": source.get("doi", ""),
        "source_url": source.get("url", ""),
        "target_provider_work_id": target.get("provider_work_id", ""),
        "target_title": target.get("title", ""),
        "target_year": target.get("year", ""),
        "target_doi": target.get("doi", ""),
        "target_url": target.get("url", ""),
        "related_provider_work_id": related_flat.get("provider_work_id", ""),
        "related_title": related_flat.get("title", ""),
        "related_year": related_flat.get("year", ""),
        "related_publication_date": related_flat.get("publication_date", ""),
        "related_type": related_flat.get("type", ""),
        "related_venue": related_flat.get("venue", ""),
        "related_journal": related_flat.get("journal", ""),
        "related_authors": related_flat.get("authors", ""),
        "related_doi": related_flat.get("doi", ""),
        "related_arxiv_id": related_flat.get("arxiv_id", ""),
        "related_pmid": related_flat.get("pmid", ""),
        "related_pmcid": related_flat.get("pmcid", ""),
        "related_url": related_flat.get("url", ""),
        "related_pdf_url": related_flat.get("pdf_url", ""),
        "related_is_open_access": related_flat.get("is_open_access", ""),
        "related_citation_count": related_flat.get("citation_count", ""),
        "related_reference_count": related_flat.get("reference_count", ""),
        "related_influential_citation_count": related_flat.get("influential_citation_count", ""),
        "contexts": contexts,
        "intents": intents,
        "is_influential": is_influential,
        "abstract": related_flat.get("abstract", ""),
        "node_key": node_key_from(provider, related_flat, doi=related_flat.get("doi", ""), title=related_flat.get("title", ""), year=related_flat.get("year", "")),
    }
    return {k: safe_str(row.get(k, "")) for k in EDGE_COLUMNS}


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: safe_str(r.get(k, "")) for k in fieldnames})


def merge_nodes(seed_rows: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    nodes: Dict[str, Dict[str, Any]] = {}

    def upsert(provider: str, flat: Dict[str, Any], role: str, seed_id: str):
        key = node_key_from(provider, flat, doi=flat.get("doi", ""), title=flat.get("title", ""), year=flat.get("year", ""))
        if key not in nodes:
            nodes[key] = {
                "node_key": key, "provider": provider,
                "provider_work_id": flat.get("provider_work_id", ""),
                "openalex_id": flat.get("openalex_id", ""),
                "semantic_scholar_paper_id": flat.get("semantic_scholar_paper_id", ""),
                "corpus_id": flat.get("corpus_id", ""),
                "doi": flat.get("doi", ""),
                "arxiv_id": flat.get("arxiv_id", ""),
                "pmid": flat.get("pmid", ""),
                "pmcid": flat.get("pmcid", ""),
                "title": flat.get("title", ""),
                "year": flat.get("year", ""),
                "publication_date": flat.get("publication_date", ""),
                "type": flat.get("type", ""),
                "venue": flat.get("venue", ""),
                "journal": flat.get("journal", ""),
                "authors": flat.get("authors", ""),
                "url": flat.get("url", ""),
                "pdf_url": flat.get("pdf_url", ""),
                "is_open_access": flat.get("is_open_access", ""),
                "citation_count": flat.get("citation_count", ""),
                "reference_count": flat.get("reference_count", ""),
                "influential_citation_count": flat.get("influential_citation_count", ""),
                "source_roles": set(),
                "seen_from_seed_ids": set(),
                "abstract": flat.get("abstract", ""),
            }
        nodes[key]["source_roles"].add(role)
        if seed_id:
            nodes[key]["seen_from_seed_ids"].add(seed_id)

    # Seed provider rows already flattened in a slightly different shape
    for r in seed_rows:
        flat = {k: r.get(k, "") for k in [
            "provider_work_id", "openalex_id", "semantic_scholar_paper_id", "corpus_id", "doi", "arxiv_id",
            "pmid", "pmcid", "title", "year", "publication_date", "type", "venue", "journal",
            "authors", "url", "pdf_url", "is_open_access", "citation_count", "reference_count",
            "influential_citation_count", "abstract",
        ]}
        upsert(r.get("provider", ""), flat, "seed", r.get("seed_row_id", ""))

    for e in edges:
        # related item is enough; seeds were inserted above
        flat = {
            "provider_work_id": e.get("related_provider_work_id", ""),
            "doi": e.get("related_doi", ""),
            "arxiv_id": e.get("related_arxiv_id", ""),
            "pmid": e.get("related_pmid", ""),
            "pmcid": e.get("related_pmcid", ""),
            "title": e.get("related_title", ""),
            "year": e.get("related_year", ""),
            "publication_date": e.get("related_publication_date", ""),
            "type": e.get("related_type", ""),
            "venue": e.get("related_venue", ""),
            "journal": e.get("related_journal", ""),
            "authors": e.get("related_authors", ""),
            "url": e.get("related_url", ""),
            "pdf_url": e.get("related_pdf_url", ""),
            "is_open_access": e.get("related_is_open_access", ""),
            "citation_count": e.get("related_citation_count", ""),
            "reference_count": e.get("related_reference_count", ""),
            "influential_citation_count": e.get("related_influential_citation_count", ""),
            "abstract": e.get("abstract", ""),
        }
        upsert(e.get("provider", ""), flat, e.get("direction", ""), e.get("seed_row_id", ""))

    out = []
    for n in nodes.values():
        n["source_roles"] = "; ".join(sorted(n["source_roles"]))
        n["seen_from_seed_ids"] = "; ".join(sorted(n["seen_from_seed_ids"]))
        out.append(n)
    return sorted(out, key=lambda x: (x.get("year", "9999"), x.get("title", "")))


def merged_seed_metadata(seed_provider_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_seed: Dict[str, Dict[str, Any]] = {}
    for r in seed_provider_rows:
        sid = r.get("seed_row_id", "")
        base = by_seed.setdefault(sid, {
            "seed_row_id": sid,
            "dataset_name": r.get("dataset_name", ""),
            "input_title": r.get("source_input_title", ""),
            "input_doi": r.get("source_input_doi", ""),
            "openalex_id": "", "s2_paper_id": "", "doi": "", "title": "", "year": "", "venue": "",
            "authors": "", "openalex_citation_count": "", "s2_citation_count": "",
            "openalex_reference_count": "", "s2_reference_count": "", "openalex_match_score": "", "s2_match_score": "",
            "openalex_match_method": "", "s2_match_method": "", "notes": "",
        })
        provider = r.get("provider")
        if provider == "openalex":
            base["openalex_id"] = r.get("openalex_id", "")
            base["openalex_citation_count"] = r.get("citation_count", "")
            base["openalex_reference_count"] = r.get("reference_count", "")
            base["openalex_match_score"] = r.get("match_score", "")
            base["openalex_match_method"] = r.get("match_method", "")
        elif provider == "semantic_scholar":
            base["s2_paper_id"] = r.get("semantic_scholar_paper_id", "")
            base["s2_citation_count"] = r.get("citation_count", "")
            base["s2_reference_count"] = r.get("reference_count", "")
            base["s2_match_score"] = r.get("match_score", "")
            base["s2_match_method"] = r.get("match_method", "")
        # prefer non-empty values, OpenAlex then S2 in input order
        for k in ["doi", "title", "year", "venue", "authors"]:
            if not base.get(k) and r.get(k):
                base[k] = r.get(k)
    return list(by_seed.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect OpenAlex + Semantic Scholar metadata and one-hop snowballing for seed papers.")
    ap.add_argument("--input", default="input/seed_papers_manifest.csv", help="Seed CSV path")
    ap.add_argument("--out", default="outputs", help="Output directory")
    ap.add_argument("--mailto", default=os.environ.get("OPENALEX_MAILTO", ""), help="Contact email sent to OpenAlex")
    ap.add_argument("--openalex-api-key", default=os.environ.get("OPENALEX_API_KEY", ""), help="OpenAlex API key")
    ap.add_argument("--s2-api-key", default=os.environ.get("S2_API_KEY", ""), help="Semantic Scholar API key (recommended)")
    ap.add_argument("--min-title-score", type=float, default=0.88, help="Minimum score for accepting title-search matches")
    ap.add_argument("--seed-ids", default="", help="Comma-separated seed row IDs to collect; empty means all")
    ap.add_argument("--allow-existing-out", action="store_true", help="Allow writing into a directory that already has run outputs")
    ap.add_argument("--providers", choices=["both", "openalex", "semantic_scholar"], default="both")
    ap.add_argument("--max-forward-citations", type=int, default=0, help="0 = all forward citations")
    ap.add_argument("--max-backward-references", type=int, default=0, help="0 = all references")
    ap.add_argument("--openalex-sleep", type=float, default=0.12)
    ap.add_argument("--s2-sleep", type=float, default=1.2)
    ap.add_argument("--refresh-cache", action="store_true")
    ap.add_argument("--skip-openalex-reference-details", action="store_true", help="Keep OpenAlex reference IDs only instead of fetching full work metadata")
    args = ap.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    existing_run_files = [
        out_dir / "seed_papers_provider_metadata.csv", out_dir / "snowball_edges.csv",
        out_dir / "run_manifest.json",
    ]
    if not args.allow_existing_out and any(path.exists() for path in existing_run_files):
        raise SystemExit(f"Refusing to overwrite an existing run directory: {out_dir}. Use a new run ID or --allow-existing-out.")
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "cache"
    raw_dir = out_dir / "raw_seed_records"
    raw_dir.mkdir(parents=True, exist_ok=True)

    seeds = read_csv_dicts(input_path)
    selected_seed_ids = {value.strip() for value in args.seed_ids.split(",") if value.strip()}
    if selected_seed_ids:
        seeds = [seed for seed in seeds if seed.get("row_id", "") in selected_seed_ids]
        missing_seed_ids = selected_seed_ids - {seed.get("row_id", "") for seed in seeds}
        if missing_seed_ids:
            raise SystemExit(f"Unknown --seed-ids: {', '.join(sorted(missing_seed_ids))}")
    cfg = ClientConfig(
        mailto=args.mailto,
        openalex_api_key=args.openalex_api_key,
        s2_api_key=args.s2_api_key,
        min_title_score=args.min_title_score,
        cache_dir=cache_dir,
        openalex_sleep=args.openalex_sleep,
        s2_sleep=args.s2_sleep,
        refresh_cache=args.refresh_cache,
    )
    http = CachedHttpClient(cfg)
    oa = OpenAlexClient(http, cfg)
    s2 = SemanticScholarClient(http, cfg)

    seed_provider_rows: List[Dict[str, Any]] = []
    backward_rows: List[Dict[str, Any]] = []
    forward_rows: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    print(f"[{now_iso()}] Starting {len(seeds)} seeds; providers={args.providers}")
    print(f"Input: {input_path.resolve()}")
    print(f"Output: {out_dir.resolve()}")

    for idx, seed in enumerate(seeds, start=1):
        sid = seed.get("row_id", f"seed{idx}")
        print(f"\n[{idx}/{len(seeds)}] {sid} {seed.get('dataset_name','')} — {seed.get('title','')[:100]}")

        if args.providers in {"both", "openalex"}:
            work, method, score, status, cache_path = oa.resolve_seed(seed)
            if work and work.get("id") and status != "low_confidence" and score >= args.min_title_score:
                raw_path = raw_dir / f"{sid}_openalex_seed.json"
                raw_path.write_text(json.dumps(work, ensure_ascii=False, indent=2), encoding="utf-8")
                row = openalex_to_row(seed, work, status, method, score, str(raw_path))
                seed_provider_rows.append(row)
                seed_flat = openalex_related_to_flat(work)
                print(f"  OpenAlex: resolved {seed_flat.get('provider_work_id')} refs={len(work.get('referenced_works') or [])} cited_by={work.get('cited_by_count')}")

                # Backward references
                ref_ids = work.get("referenced_works") or []
                for i, rid in enumerate(ref_ids, start=1):
                    if args.max_backward_references and i > args.max_backward_references:
                        break
                    if args.skip_openalex_reference_details:
                        related = {"provider_work_id": rid.rsplit('/', 1)[-1], "title": "", "url": rid}
                    else:
                        related_work, st, _ = oa.fetch_work(rid)
                        related = openalex_related_to_flat(related_work or {"id": rid})
                    backward_rows.append(make_edge(seed, "openalex", "backward_reference", seed_flat, related, i))

                # Forward citations
                for i, citing_work in enumerate(oa.iter_cited_by(work, max_records=args.max_forward_citations), start=1):
                    related = openalex_related_to_flat(citing_work)
                    forward_rows.append(make_edge(seed, "openalex", "forward_citation", seed_flat, related, i))

                summary_rows.append({
                    "seed_row_id": sid, "provider": "openalex", "status": "resolved", "match_method": method,
                    "match_score": f"{score:.4f}", "reported_reference_count": len(work.get("referenced_works") or []),
                    "downloaded_reference_rows": len([r for r in backward_rows if r.get("seed_row_id") == sid and r.get("provider") == "openalex"]),
                    "reported_citation_count": work.get("cited_by_count", ""),
                    "downloaded_citation_rows": len([r for r in forward_rows if r.get("seed_row_id") == sid and r.get("provider") == "openalex"]),
                    "run_time_utc": now_iso(),
                })
            else:
                print(f"  OpenAlex: unresolved ({method}, score={score:.3f})")
                unresolved.append({
                    "seed_row_id": sid, "provider": "openalex", "reason": method, "score": f"{score:.4f}",
                    "candidate_provider_work_id": (work or {}).get("id", ""),
                    "candidate_title": (work or {}).get("title", ""),
                    "candidate_year": (work or {}).get("publication_year", ""),
                    "cache_path": cache_path,
                })
                summary_rows.append({"seed_row_id": sid, "provider": "openalex", "status": "unresolved", "match_method": method, "match_score": f"{score:.4f}", "run_time_utc": now_iso()})

        if args.providers in {"both", "semantic_scholar"}:
            paper, method, score, status, cache_path = s2.resolve_seed(seed)
            if paper and paper.get("paperId") and status != "low_confidence" and score >= args.min_title_score:
                raw_path = raw_dir / f"{sid}_semantic_scholar_seed.json"
                raw_path.write_text(json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8")
                row = s2_to_row(seed, paper, status, method, score, str(raw_path))
                seed_provider_rows.append(row)
                seed_flat = s2_related_to_flat(paper)
                paper_id = paper.get("paperId")
                print(f"  Semantic Scholar: resolved {paper_id} refs={paper.get('referenceCount')} cited_by={paper.get('citationCount')}")

                ref_counter = 0
                for i, rel in enumerate(s2.iter_relations(paper_id, "references", max_records=args.max_backward_references), start=1):
                    cited = rel.get("citedPaper") or {}
                    related = s2_related_to_flat(cited)
                    ref_counter += 1
                    backward_rows.append(make_edge(
                        seed, "semantic_scholar", "backward_reference", seed_flat, related, i,
                        contexts=rel.get("contexts", ""), intents=rel.get("intents", ""), is_influential=rel.get("isInfluential", ""),
                    ))

                cit_counter = 0
                for i, rel in enumerate(s2.iter_relations(paper_id, "citations", max_records=args.max_forward_citations), start=1):
                    citing = rel.get("citingPaper") or {}
                    related = s2_related_to_flat(citing)
                    cit_counter += 1
                    forward_rows.append(make_edge(
                        seed, "semantic_scholar", "forward_citation", seed_flat, related, i,
                        contexts=rel.get("contexts", ""), intents=rel.get("intents", ""), is_influential=rel.get("isInfluential", ""),
                    ))

                summary_rows.append({
                    "seed_row_id": sid, "provider": "semantic_scholar", "status": "resolved", "match_method": method,
                    "match_score": f"{score:.4f}", "reported_reference_count": paper.get("referenceCount", ""),
                    "downloaded_reference_rows": ref_counter, "reported_citation_count": paper.get("citationCount", ""),
                    "downloaded_citation_rows": cit_counter, "run_time_utc": now_iso(),
                })
            else:
                print(f"  Semantic Scholar: unresolved ({method}, score={score:.3f})")
                unresolved.append({
                    "seed_row_id": sid, "provider": "semantic_scholar", "reason": method, "score": f"{score:.4f}",
                    "candidate_provider_work_id": (paper or {}).get("paperId", ""),
                    "candidate_title": (paper or {}).get("title", ""),
                    "candidate_year": (paper or {}).get("year", ""),
                    "cache_path": cache_path,
                })
                summary_rows.append({"seed_row_id": sid, "provider": "semantic_scholar", "status": "unresolved", "match_method": method, "match_score": f"{score:.4f}", "run_time_utc": now_iso()})

    all_edges = backward_rows + forward_rows
    nodes = merge_nodes(seed_provider_rows, all_edges)
    merged_seed_rows = merged_seed_metadata(seed_provider_rows)

    write_csv(out_dir / "seed_papers_provider_metadata.csv", seed_provider_rows, SEED_PROVIDER_COLUMNS)
    write_csv(out_dir / "seed_papers_merged_metadata.csv", merged_seed_rows, [
        "seed_row_id", "dataset_name", "input_title", "input_doi", "openalex_id", "s2_paper_id", "doi",
        "title", "year", "venue", "authors", "openalex_citation_count", "s2_citation_count",
        "openalex_reference_count", "s2_reference_count", "openalex_match_score", "s2_match_score",
        "openalex_match_method", "s2_match_method", "notes",
    ])
    write_csv(out_dir / "backward_references.csv", backward_rows, EDGE_COLUMNS)
    write_csv(out_dir / "forward_citations.csv", forward_rows, EDGE_COLUMNS)
    write_csv(out_dir / "snowball_edges.csv", all_edges, EDGE_COLUMNS)
    write_csv(out_dir / "snowball_nodes.csv", nodes, NODE_COLUMNS)
    write_csv(out_dir / "run_summary.csv", summary_rows, [
        "seed_row_id", "provider", "status", "match_method", "match_score",
        "reported_reference_count", "downloaded_reference_rows", "reported_citation_count", "downloaded_citation_rows",
        "run_time_utc",
    ])
    write_csv(out_dir / "unresolved_seeds.csv", unresolved, [
        "seed_row_id", "provider", "reason", "score", "candidate_provider_work_id",
        "candidate_title", "candidate_year", "cache_path",
    ])
    write_csv(out_dir / "relation_errors.csv", s2.relation_errors, [
        "paper_id", "relation", "offset", "status", "cache_path",
    ])

    manifest = {
        "created_utc": now_iso(),
        "input": str(input_path),
        "providers": args.providers,
        "seed_count": len(seeds),
        "seed_provider_metadata_rows": len(seed_provider_rows),
        "backward_reference_rows": len(backward_rows),
        "forward_citation_rows": len(forward_rows),
        "snowball_edge_rows": len(all_edges),
        "snowball_node_rows": len(nodes),
        "unresolved_count": len(unresolved),
        "max_forward_citations": args.max_forward_citations,
        "max_backward_references": args.max_backward_references,
        "openalex_mailto_used": bool(args.mailto),
        "openalex_api_key_used": bool(args.openalex_api_key),
        "semantic_scholar_api_key_used": bool(args.s2_api_key),
        "min_title_score": args.min_title_score,
        "selected_seed_ids": sorted(selected_seed_ids),
        "relation_error_rows": len(s2.relation_errors),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nDone.")
    for name in [
        "seed_papers_provider_metadata.csv", "seed_papers_merged_metadata.csv", "backward_references.csv",
        "forward_citations.csv", "snowball_edges.csv", "snowball_nodes.csv", "run_summary.csv",
        "unresolved_seeds.csv", "relation_errors.csv", "run_manifest.json",
    ]:
        print(f"  {out_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
