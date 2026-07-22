from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .io_utils import sha256_text


@dataclass(frozen=True)
class Work:
    paper_id: str
    rank: int
    title: str
    year: str = ""
    authors: str = ""
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pmid: str = ""
    pmcid: str = ""
    openalex_id: str = ""
    semantic_scholar_id: str = ""
    landing_url: str = ""
    pdf_url: str = ""
    is_open_access: bool = False
    screening_decision: str = ""
    screening_confidence: str = ""
    likely_paper_type: str = ""
    priority_score: str = ""
    source_row: dict[str, str] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class Candidate:
    paper_id: str
    source: str
    url: str
    artifact_type: str
    score: int
    discovery_method: str
    license: str = ""
    version: str = ""
    host_type: str = ""
    rights_status: str = "unknown"
    is_oa: bool = False
    expected_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def candidate_id(self) -> str:
        return "FTC_" + sha256_text(f"{self.paper_id}|{self.source}|{self.artifact_type}|{self.url}")[:20]

    def as_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["candidate_id"] = self.candidate_id
        return row


@dataclass(frozen=True)
class DownloadedArtifact:
    paper_id: str
    source: str
    artifact_type: str
    source_url: str
    final_url: str
    stored_path: str
    sha256: str
    size_bytes: int
    mime_type: str
    license: str
    version: str
    host_type: str
    rights_status: str
    candidate_id: str
