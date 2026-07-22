from pathlib import Path

import fitz

from agri_fulltext.acquisition import import_local_artifact
from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import read_csv
from agri_fulltext.models import Work
from agri_fulltext.preflight import inspect_pdf


def test_pdf_preflight_and_import(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    pdf = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a digitally born academic paper with enough text for extraction. " * 5)
    doc.save(pdf)
    result = inspect_pdf(pdf)
    assert result["classification"] == "born_digital"
    settings = load_settings(repo)
    work = Work(paper_id="doi:10.1/test", rank=1, title="Test")
    row = import_local_artifact(settings, work, pdf, rights_status="local_research_only")
    assert (repo / row["stored_path"]).exists()
    _, rows = read_csv(settings.artifact_registry)
    assert rows[0]["rights_status"] == "local_research_only"


def test_pmc_oai_wrapper_is_classified_as_jats(tmp_path: Path):
    from agri_fulltext.acquisition import _validate_file

    source = tmp_path / "pmc-oai.xml"
    source.write_text(
        """<?xml version='1.0'?>
        <OAI-PMH xmlns='http://www.openarchives.org/OAI/2.0/'>
          <GetRecord><record><metadata>
            <article xmlns='http://jats.nlm.nih.gov'><front/><body><p>Text</p></body></article>
          </metadata></record></GetRecord>
        </OAI-PMH>""",
        encoding="utf-8",
    )
    artifact_type, mime = _validate_file(source, expected_type="jats_xml", max_bytes=1_000_000)
    assert artifact_type == "jats_xml"
    assert mime == "application/xml"


def test_pmc_oai_error_wrapper_is_rejected(tmp_path: Path):
    import pytest
    from agri_fulltext.acquisition import _validate_file

    source = tmp_path / "pmc-oai-error.xml"
    source.write_text(
        """<?xml version='1.0'?><OAI-PMH xmlns='http://www.openarchives.org/OAI/2.0/'><error code='idDoesNotExist'>none</error></OAI-PMH>""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Expected jats_xml"):
        _validate_file(source, expected_type="jats_xml", max_bytes=1_000_000)
