"""Batch-process remaining papers with direct Docling Python API (faster than subprocess)."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv
from agri_fulltext.schema import EXTRACTION_REGISTRY_FIELDS
import json

repo = Path('.')

# Papers still needing Docling: ranks 92, 94, 95, 96, 98, 99
papers = [
    ('doi:10.48550/arxiv.2503.05568', 'data/raw/fulltext/doi_10.48550_arxiv.2503.05568/7465a333fced4b54/source.pdf'),
    ('doi:10.1371/journal.pone.0077151', 'data/raw/fulltext/doi_10.1371_journal.pone.0077151/148fc3671e2e1c0f/source.pdf'),
    ('doi:10.1016/j.dib.2020.105833', None),  # has publisher XML
    ('doi:10.1177/0278364917720510', None),  # has publisher XML
    ('doi:10.3390/agronomy16050536', 'data/raw/fulltext/doi_10.3390_agronomy16050536/f3e197b796f4ab4f/source.pdf'),
    ('doi:10.18420/giljt2025_02', 'data/raw/fulltext/doi_10.18420_giljt2025_02/b6e62fe184cd0900/source.pdf'),
]

from agri_fulltext.processing import _run_docling

class FakeSettings:
    docling_mode = 'local'
    docling_device = 'auto'
    docling_threads = 4
    docling_timeout_seconds = 600
    repo = repo

settings = FakeSettings()

for pid, pdf_rel in papers:
    if pdf_rel is None:
        print(f'{pid:50s} | XML-only, skipping Docling')
        continue
    pdf_path = repo / pdf_rel
    if not pdf_path.exists():
        print(f'{pid:50s} | PDF not found at {pdf_path}')
        continue
    output_dir = repo / f'tmp_docling/{pid.replace(":","_").replace("/","_")}'
    preflight = {'classification': 'born_digital', 'recommended_ocr': False}
    print(f'{pid:50s} | running Docling...')
    try:
        result = _run_docling(settings, pdf_path, output_dir, preflight)
        status = result.get('status', 'unknown')
        chars = result.get('markdown_chars', 0)
        print(f'  -> status={status}, chars={chars}')
    except Exception as e:
        print(f'  -> FAILED: {e}')
