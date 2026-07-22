from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

import fitz

from .io_utils import sha256_file


def inspect_pdf(path: Path) -> dict[str, Any]:
    path = path.resolve()
    doc = fitz.open(path)
    if doc.needs_pass:
        return {
            "path": str(path),
            "sha256": sha256_file(path),
            "encrypted": True,
            "page_count": doc.page_count,
            "classification": "encrypted",
            "recommended_ocr": False,
            "manual_review": True,
        }

    chars_per_page: list[int] = []
    blocks_per_page: list[int] = []
    images_per_page: list[int] = []
    tables_per_page: list[int] = []
    two_column_pages = 0
    for page in doc:
        text = page.get_text("text") or ""
        blocks = [block for block in page.get_text("blocks") if len(str(block[4]).strip()) >= 20]
        images = page.get_images(full=True)
        chars_per_page.append(len(text.strip()))
        blocks_per_page.append(len(blocks))
        images_per_page.append(len(images))
        try:
            tables_per_page.append(len(page.find_tables().tables))
        except Exception:
            tables_per_page.append(0)
        width = float(page.rect.width or 1)
        left = sum(1 for block in blocks if float(block[0]) < width * 0.42)
        right = sum(1 for block in blocks if float(block[0]) > width * 0.42)
        if left >= 2 and right >= 2:
            two_column_pages += 1

    pages = max(1, doc.page_count)
    text_pages = sum(1 for value in chars_per_page if value >= 80)
    empty_text_pages = sum(1 for value in chars_per_page if value < 20)
    text_page_ratio = text_pages / pages
    image_page_ratio = sum(1 for value in images_per_page if value > 0) / pages
    if text_page_ratio >= 0.85:
        classification = "born_digital"
    elif text_page_ratio <= 0.15:
        classification = "scanned"
    else:
        classification = "hybrid"
    complexity = "complex" if (two_column_pages / pages >= 0.25 or sum(tables_per_page) > 0) else "simple"
    recommended_ocr = classification in {"scanned", "hybrid"}
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "encrypted": False,
        "page_count": doc.page_count,
        "classification": classification,
        "layout_complexity": complexity,
        "recommended_ocr": recommended_ocr,
        "force_ocr_recommended": classification == "scanned",
        "manual_review": classification in {"scanned", "hybrid"} or complexity == "complex",
        "total_text_characters": sum(chars_per_page),
        "median_text_characters_per_page": int(statistics.median(chars_per_page)) if chars_per_page else 0,
        "text_page_ratio": round(text_page_ratio, 4),
        "empty_text_page_count": empty_text_pages,
        "image_count": sum(images_per_page),
        "image_page_ratio": round(image_page_ratio, 4),
        "detected_table_count": sum(tables_per_page),
        "two_column_page_count": two_column_pages,
        "two_column_page_ratio": round(two_column_pages / pages, 4),
        "blocks_per_page_median": int(statistics.median(blocks_per_page)) if blocks_per_page else 0,
        "chars_per_page": chars_per_page,
    }
