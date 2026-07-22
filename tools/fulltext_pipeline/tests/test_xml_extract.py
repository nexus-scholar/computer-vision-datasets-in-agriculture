import json
from pathlib import Path

from agri_fulltext.xml_extract import xml_to_outputs


def test_jats_extraction(tmp_path: Path):
    source = tmp_path / "paper.xml"
    source.write_text("""<?xml version='1.0'?>
    <article><front><article-meta><title-group><article-title>Dataset paper</article-title></title-group>
    <abstract><p>An abstract.</p></abstract></article-meta></front>
    <body><sec><title>Methods</title><p>We collected images.</p></sec></body>
    <back><ref-list><ref id='R1'><element-citation><person-group><name><surname>Doe</surname></name></person-group>
    <article-title>Prior work</article-title><year>2020</year><pub-id pub-id-type='doi'>10.1/x</pub-id>
    </element-citation></ref></ref-list></back></article>""", encoding="utf-8")
    metrics = xml_to_outputs(source, tmp_path / "out", "p1", "abc")
    assert metrics["xml_kind"] == "jats"
    assert metrics["reference_count"] == 1
    assert "Methods" in (tmp_path / "out/document.md").read_text()
    ref = json.loads((tmp_path / "out/references.jsonl").read_text().splitlines()[0])
    assert ref["doi"] == "10.1/x"
