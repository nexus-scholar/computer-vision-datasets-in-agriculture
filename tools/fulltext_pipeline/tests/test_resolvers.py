from pathlib import Path

import requests

from agri_fulltext.config import load_settings
from agri_fulltext.models import Work
from agri_fulltext.resolvers import (
    ArxivResolver,
    DirectResolver,
    EuropePmcResolver,
    PmcIdConverterResolver,
    PmcOaiResolver,
    auto_download_allowed,
)


def settings(tmp_path: Path):
    return load_settings(tmp_path)


def test_identifier_resolvers_are_deterministic(tmp_path: Path):
    cfg = settings(tmp_path)
    session = requests.Session()
    work = Work(
        paper_id="p1", rank=1, title="x", arxiv_id="2501.12345", pmcid="PMC123",
        pdf_url="https://example.org/paper.pdf", is_open_access=True,
    )
    direct = DirectResolver(cfg, session).resolve(work)
    arxiv = ArxivResolver(cfg, session).resolve(work)
    pmc = EuropePmcResolver(cfg, session).resolve(work)
    pmc_oai = PmcOaiResolver(cfg, session).resolve(work)
    assert direct[0].artifact_type == "pdf"
    assert arxiv[0].url.endswith("2501.12345")
    assert {item.artifact_type for item in pmc} == {"pdf", "jats_xml"}
    assert pmc_oai[0].artifact_type == "jats_xml"
    assert "oai:pubmedcentral.nih.gov:123" in pmc_oai[0].url
    assert all(auto_download_allowed(item, cfg) for item in [*direct, *arxiv, *pmc, *pmc_oai])


def test_pmc_id_converter_recovers_exact_pmcid(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FULLTEXT_CONTACT_EMAIL", "researcher@example.org")
    cfg = settings(tmp_path)
    resolver = PmcIdConverterResolver(cfg, requests.Session())
    monkeypatch.setattr(
        resolver,
        "get_json",
        lambda *args, **kwargs: {
            "records": [{
                "requested-id": "10.1234/example",
                "doi": "10.1234/example",
                "pmid": "123456",
                "pmcid": "PMC999999",
            }]
        },
    )
    work = Work(paper_id="p2", rank=2, title="x", doi="10.1234/example")
    candidates = resolver.resolve(work)
    assert {item.artifact_type for item in candidates} == {"pdf", "jats_xml"}
    assert all("PMC999999" in (item.url + str(item.metadata)) for item in candidates)
    assert all(item.metadata["requested_id"] == "10.1234/example" for item in candidates)


def test_pmc_id_converter_skips_without_contact_email(tmp_path: Path):
    cfg = settings(tmp_path)
    resolver = PmcIdConverterResolver(cfg, requests.Session())
    work = Work(paper_id="p3", rank=3, title="x", doi="10.1234/example")
    assert resolver.resolve(work) == []
