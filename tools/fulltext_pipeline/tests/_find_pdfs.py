"""Find PDF paths from artifact registry and re-run Docling via CLI on remaining papers."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

repo = Path('.')
_, art = read_csv(repo / 'data/curated/fulltext/artifact_registry.csv')

# Find PDF paths for papers that still need Docling
pids = ['doi:10.48550/arxiv.2503.05568', 'doi:10.1371/journal.pone.0077151',
        'doi:10.18420/giljt2025_02']
for a in art:
    if a.get('paper_id','') in pids and a.get('artifact_type') == 'pdf' and a.get('status') == 'success':
        stored = a.get('stored_path','')
        full = repo / stored
        print(f'{a["paper_id"]:50s} | stored_path={stored}')
        print(f'  exists={full.exists()}, size={full.stat().st_size if full.exists() else 0}')
