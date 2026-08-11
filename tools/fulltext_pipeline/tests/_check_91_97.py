"""Check ranks 91 and 97 status."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ta = read_csv(Path('data/curated/screening/title_abstract_decisions.csv'))
for r in ta:
    rank = r.get('rank','')
    if rank in ('91','97'):
        print(f'TA Rank {rank}: decision={r["decision"]}, title={r["title"][:60]}')

_, ext = read_csv(Path('data/curated/fulltext/extraction_registry.csv'))
for r in ext:
    rank = r.get('rank','')
    if rank in ('91','97'):
        print(f'Ext Rank {rank}: paper_id={r.get("paper_id","")[:50]}, qa={r.get("qa_status","?")}, output={r.get("output_dir","?")}')
