from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from lxml import etree

from .io_utils import sha256_text


def local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def element_text(element: etree._Element | None) -> str:
    return normalize_space(" ".join(element.itertext())) if element is not None else ""


def xml_to_outputs(path: Path, output_dir: Path, paper_id: str, source_sha256: str) -> dict[str, Any]:
    tree = etree.parse(str(path))
    root = tree.getroot()
    kind = "tei" if local_name(root).lower() == "tei" else "jats"
    output_dir.mkdir(parents=True, exist_ok=True)
    if kind == "tei":
        markdown, references, citations, tables, figures, formulas = _tei(tree)
    else:
        markdown, references, citations, tables, figures, formulas = _jats(tree)
    (output_dir / "document.md").write_text(markdown.rstrip() + "\n", encoding="utf-8")
    _write_jsonl(output_dir / "references.jsonl", references)
    _write_jsonl(output_dir / "citation_contexts.jsonl", citations)
    _write_jsonl(output_dir / "tables.jsonl", tables)
    _write_jsonl(output_dir / "figures.jsonl", figures)
    _write_jsonl(output_dir / "formulas.jsonl", formulas)
    chunks = _markdown_chunks(markdown, paper_id, source_sha256, source=f"{kind}_xml")
    _write_jsonl(output_dir / "chunks.jsonl", chunks)
    return {
        "xml_kind": kind,
        "markdown_chars": len(markdown),
        "reference_count": len(references),
        "citation_context_count": len(citations),
        "table_count": len(tables),
        "figure_count": len(figures),
        "formula_count": len(formulas),
        "chunk_count": len(chunks),
    }


def _tei(tree: etree._ElementTree) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    title = element_text(tree.find(".//tei:titleStmt/tei:title", ns)) or element_text(tree.find(".//tei:title", ns))
    lines = [f"# {title}" if title else "# Untitled scholarly document", ""]
    body = tree.find(".//tei:text/tei:body", ns)
    if body is not None:
        for div in body.xpath(".//tei:div", namespaces=ns):
            head = element_text(div.find("tei:head", ns))
            if head:
                lines.extend([f"## {head}", ""])
            for p in div.findall("tei:p", ns):
                text = element_text(p)
                if text:
                    lines.extend([text, ""])
    references: list[dict[str, Any]] = []
    for index, item in enumerate(tree.xpath(".//tei:listBibl/*", namespaces=ns), start=1):
        item_id = item.get("{http://www.w3.org/XML/1998/namespace}id") or f"ref_{index:04d}"
        title_el = item.find(".//tei:title[@level='a']", ns)
        if title_el is None:
            title_el = item.find(".//tei:title", ns)
        authors = [element_text(author) for author in item.findall(".//tei:author", ns) if element_text(author)]
        date = item.find(".//tei:date", ns)
        doi_nodes = item.xpath(".//tei:idno[translate(@type,'doi','DOI')='DOI']", namespaces=ns)
        references.append(
            {
                "reference_id": item_id,
                "title": element_text(title_el),
                "authors": authors,
                "year": (date.get("when") if date is not None else "") or element_text(date),
                "doi": element_text(doi_nodes[0]) if doi_nodes else "",
                "raw_text": element_text(item),
                "coordinates": item.get("coords", ""),
            }
        )
    citations: list[dict[str, Any]] = []
    for index, ref in enumerate(tree.xpath(".//tei:ref[@type='bibr']", namespaces=ns), start=1):
        parent = ref.getparent()
        citations.append(
            {
                "citation_context_id": f"ctx_{index:05d}",
                "target": ref.get("target", ""),
                "marker": element_text(ref),
                "context": element_text(parent),
                "coordinates": ref.get("coords", ""),
            }
        )
    tables = [_tei_figure(item, index, "table") for index, item in enumerate(tree.xpath(".//tei:figure[@type='table']", namespaces=ns), start=1)]
    figures = [_tei_figure(item, index, "figure") for index, item in enumerate(tree.xpath(".//tei:figure[not(@type='table')]", namespaces=ns), start=1)]
    formulas = [
        {
            "id": item.get("{http://www.w3.org/XML/1998/namespace}id") or f"formula_{index:04d}",
            "content": element_text(item),
            "coordinates": item.get("coords", ""),
            "raw_xml": _serialize_xml(item),
        }
        for index, item in enumerate(tree.xpath(".//tei:formula", namespaces=ns), start=1)
    ]
    return "\n".join(lines), references, citations, tables, figures, formulas


def _tei_figure(item: etree._Element, index: int, kind: str) -> dict[str, Any]:
    labels = item.xpath(".//*[local-name()='label']")
    descriptions = item.xpath(".//*[local-name()='figDesc']")
    heads = item.xpath(".//*[local-name()='head']")
    return {
        "id": item.get("{http://www.w3.org/XML/1998/namespace}id") or f"{kind}_{index:04d}",
        "label": element_text(labels[0]) if labels else "",
        "caption": (element_text(descriptions[0]) if descriptions else "") or (element_text(heads[0]) if heads else ""),
        "content": element_text(item),
        "coordinates": item.get("coords", ""),
        "raw_xml": _serialize_xml(item),
    }


def _jats(tree: etree._ElementTree) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    title_nodes = tree.xpath("//*[local-name()='article-title']")
    title = element_text(title_nodes[0]) if title_nodes else ""
    lines = [f"# {title}" if title else "# Untitled scholarly document", ""]
    for abstract in tree.xpath("//*[local-name()='abstract']"):
        text = element_text(abstract)
        if text:
            lines.extend(["## Abstract", "", text, ""])
            break
    for section in tree.xpath("//*[local-name()='body']//*[local-name()='sec']"):
        direct_titles = section.xpath("./*[local-name()='title']")
        heading = element_text(direct_titles[0]) if direct_titles else ""
        if heading:
            lines.extend([f"## {heading}", ""])
        for paragraph in section.xpath("./*[local-name()='p']"):
            text = element_text(paragraph)
            if text:
                lines.extend([text, ""])
    references: list[dict[str, Any]] = []
    for index, item in enumerate(tree.xpath("//*[local-name()='ref-list']/*[local-name()='ref']"), start=1):
        reference_id = item.get("id") or f"ref_{index:04d}"
        titles = item.xpath(".//*[local-name()='article-title'] | .//*[local-name()='source']")
        year_nodes = item.xpath(".//*[local-name()='year']")
        doi_nodes = item.xpath(".//*[local-name()='pub-id' and translate(@pub-id-type,'doi','DOI')='DOI']")
        surname_nodes = item.xpath(".//*[local-name()='name']")
        references.append(
            {
                "reference_id": reference_id,
                "title": element_text(titles[0]) if titles else "",
                "authors": [element_text(node) for node in surname_nodes if element_text(node)],
                "year": element_text(year_nodes[0]) if year_nodes else "",
                "doi": element_text(doi_nodes[0]) if doi_nodes else "",
                "raw_text": element_text(item),
                "coordinates": "",
            }
        )
    citations: list[dict[str, Any]] = []
    for index, xref in enumerate(tree.xpath("//*[local-name()='xref' and @ref-type='bibr']"), start=1):
        citations.append(
            {
                "citation_context_id": f"ctx_{index:05d}",
                "target": xref.get("rid", ""),
                "marker": element_text(xref),
                "context": element_text(xref.getparent()),
                "coordinates": "",
            }
        )
    tables = []
    for index, item in enumerate(tree.xpath("//*[local-name()='table-wrap']"), start=1):
        tables.append(
            {
                "id": item.get("id") or f"table_{index:04d}",
                "label": element_text(_first(item.xpath("./*[local-name()='label']"))),
                "caption": element_text(_first(item.xpath("./*[local-name()='caption']"))),
                "content": element_text(item),
                "coordinates": "",
                "rows": _jats_table_rows(item),
                "raw_xml": _serialize_xml(item),
            }
        )
    figures = []
    for index, item in enumerate(tree.xpath("//*[local-name()='fig']"), start=1):
        graphics = item.xpath(".//*[local-name()='graphic' or local-name()='inline-graphic']")
        hrefs = [
            node.get("{http://www.w3.org/1999/xlink}href") or node.get("href") or ""
            for node in graphics
        ]
        figures.append(
            {
                "id": item.get("id") or f"figure_{index:04d}",
                "label": element_text(_first(item.xpath("./*[local-name()='label']"))),
                "caption": element_text(_first(item.xpath("./*[local-name()='caption']"))),
                "content": element_text(item),
                "coordinates": "",
                "graphic_hrefs": [value for value in hrefs if value],
                "raw_xml": _serialize_xml(item),
            }
        )
    formulas = []
    for index, item in enumerate(
        tree.xpath("//*[local-name()='disp-formula' or local-name()='inline-formula']"),
        start=1,
    ):
        formulas.append(
            {
                "id": item.get("id") or f"formula_{index:04d}",
                "content": element_text(item),
                "coordinates": "",
                "raw_xml": _serialize_xml(item),
            }
        )
    return "\n".join(lines), references, citations, tables, figures, formulas


def _serialize_xml(element: etree._Element) -> str:
    return etree.tostring(element, encoding="unicode", with_tail=False)


def _jats_table_rows(table_wrap: etree._Element) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    for row in table_wrap.xpath(".//*[local-name()='table']//*[local-name()='tr']"):
        cells: list[dict[str, Any]] = []
        for cell in row.xpath("./*[local-name()='th' or local-name()='td']"):
            cells.append(
                {
                    "kind": local_name(cell).lower(),
                    "text": element_text(cell),
                    "colspan": int(cell.get("colspan") or 1),
                    "rowspan": int(cell.get("rowspan") or 1),
                }
            )
        if cells:
            rows.append(cells)
    return rows


def _first(items: list[Any]) -> Any | None:
    return items[0] if items else None


def _markdown_chunks(markdown: str, paper_id: str, source_sha256: str, source: str, max_chars: int = 6000) -> list[dict[str, Any]]:
    sections: list[tuple[str, list[str]]] = []
    heading = "Document"
    body: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            if body:
                sections.append((heading, body))
            heading = line.lstrip("# ").strip() or "Document"
            body = []
        else:
            body.append(line)
    if body:
        sections.append((heading, body))
    chunks: list[dict[str, Any]] = []
    for section, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        for offset in range(0, len(text), max_chars):
            piece = text[offset : offset + max_chars].strip()
            if not piece:
                continue
            chunk_id = "FTC_" + sha256_text(f"{paper_id}|{source_sha256}|{source}|{section}|{offset}")[:20]
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "paper_id": paper_id,
                    "source_sha256": source_sha256,
                    "source_representation": source,
                    "section_path": section,
                    "page_start": None,
                    "page_end": None,
                    "text": piece,
                    "needs_visual": False,
                    "table_refs": [],
                    "figure_refs": [],
                    "citation_refs": [],
                }
            )
    return chunks


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
