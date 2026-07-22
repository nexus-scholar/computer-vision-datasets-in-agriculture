from pathlib import Path

from agri_fulltext.config import load_settings
from agri_fulltext.io_utils import atomic_write_csv, read_csv, sha256_file
from agri_fulltext.processing import process_registered_artifacts
from agri_fulltext.schema import ARTIFACT_REGISTRY_FIELDS


def test_process_registered_jats(tmp_path: Path):
    repo = tmp_path / "repo"
    source = repo / "data/raw/fulltext/p1/abc/source.xml"
    source.parent.mkdir(parents=True)
    source.write_text("""<article><front><article-meta><title-group><article-title>Paper</article-title></title-group></article-meta></front>
    <body><sec><title>Methods</title><p>We collected agricultural image data and evaluated a segmentation model.</p></sec></body>
    <back><ref-list><ref id='R1'><mixed-citation>Reference one</mixed-citation></ref></ref-list></back></article>""", encoding="utf-8")
    settings = load_settings(repo)
    atomic_write_csv(settings.artifact_registry, ARTIFACT_REGISTRY_FIELDS, [{
        "artifact_id": "a1", "paper_id": "p1", "rank": "1", "title": "Paper", "source": "manual",
        "artifact_type": "jats_xml", "stored_path": str(source.relative_to(repo)), "sha256": sha256_file(source),
        "size_bytes": source.stat().st_size, "mime_type": "application/xml", "source_url": "", "final_url": "",
        "license": "cc-by", "version": "publishedVersion", "host_type": "publisher", "rights_status": "open_license",
        "acquired_at": "2026-01-01T00:00:00Z", "run_id": "r1", "candidate_id": "", "status": "success", "notes": "",
    }])
    out = process_registered_artifacts(settings, run_docling=False, run_grobid=False, out_dir=repo / "outputs/fulltext/processing/test")
    _, rows = read_csv(settings.extraction_registry)
    assert rows[0]["publisher_xml_status"] == "success"
    paper_dir = repo / rows[0]["output_dir"]
    assert (paper_dir / "llm/paper.md").exists()
    assert (paper_dir / "llm/chunks.jsonl").exists()
