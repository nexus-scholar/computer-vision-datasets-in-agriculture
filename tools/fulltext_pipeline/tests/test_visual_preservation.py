import json
from pathlib import Path

from agri_fulltext.processing import _copy_docling_assets, _docling_visual_inventory
from agri_fulltext.xml_extract import xml_to_outputs


def test_jats_preserves_table_spans_and_formulas(tmp_path: Path):
    source = tmp_path / "paper.xml"
    source.write_text(
        """<article xmlns:xlink='http://www.w3.org/1999/xlink'>
        <front><article-meta><title-group><article-title>Structured paper</article-title></title-group></article-meta></front>
        <body><sec><title>Results</title><p>Text.</p>
          <table-wrap id='T1'><label>Table 1</label><caption><p>Metrics</p></caption><table>
            <tr><th colspan='2'>Model</th></tr><tr><td rowspan='2'>A</td><td>0.9</td></tr>
          </table></table-wrap>
          <fig id='F1'><caption><p>Architecture</p></caption><graphic xlink:href='fig1.png'/></fig>
          <disp-formula id='EQ1'><tex-math>E=mc^2</tex-math></disp-formula>
        </sec></body></article>""",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    metrics = xml_to_outputs(source, out, "p1", "abc")
    assert metrics["table_count"] == 1
    assert metrics["figure_count"] == 1
    assert metrics["formula_count"] == 1
    table = json.loads((out / "tables.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert table["rows"][0][0]["colspan"] == 2
    figure = json.loads((out / "figures.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert figure["graphic_hrefs"] == ["fig1.png"]
    formula = json.loads((out / "formulas.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert formula["id"] == "EQ1"
    assert "E=mc^2" in formula["content"]


def test_docling_visual_inventory_and_asset_copy(tmp_path: Path):
    payload = {
        "items": [
            {"label": "table", "id": "t1", "prov": [{"page_no": 2}]},
            {"label": "picture", "id": "f1"},
            {"label": "formula", "id": "eq1"},
        ]
    }
    tables, figures, formulas = _docling_visual_inventory(payload)
    assert [row["id"] for row in tables] == ["t1"]
    assert [row["id"] for row in figures] == ["f1"]
    assert [row["id"] for row in formulas] == ["eq1"]

    output = tmp_path / "docling"
    normalized = output / "normalized"
    asset = output / "paper_artifacts" / "figure.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"image")
    normalized.mkdir()
    _copy_docling_assets(output, normalized)
    assert (normalized / "paper_artifacts" / "figure.png").read_bytes() == b"image"
