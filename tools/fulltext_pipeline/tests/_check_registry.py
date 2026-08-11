"""Check all extraction records for ranks 43, 47, 70, 71."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ext = read_csv(Path('data/curated/fulltext/extraction_registry.csv'))
for r in ext:
    rank = r.get('rank', '')
    if rank in ('43','47','70','71'):
        print(f'Rank {rank}: qa={r.get("qa_status","?")} created={r.get("created_at","?")} output={r.get("output_dir","?")}')
