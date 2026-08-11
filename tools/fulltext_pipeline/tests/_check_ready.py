"""Check which batch 5 papers are ready for extraction."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

repo = Path('.')
_, art = read_csv(repo / 'data/curated/fulltext/artifact_registry.csv')
_, reg = read_csv(repo / 'data/curated/fulltext/extraction_registry.csv')
_, queue = read_csv(repo / 'outputs/fulltext/acquisition/queue_20260729T182430Z/fulltext_queue.csv')

# Papers with artifacts
art_ids = set()
for a in art:
    pid = a.get('paper_id','')
    status = a.get('status','')
    if status == 'success':
        art_ids.add(pid)

# Papers already extracted
ext_ids = set(r.get('paper_id','') for r in reg)

print('Batch 5 papers ready for extraction:')
for q in queue:
    pid = q.get('paper_id','')
    rank = q.get('rank','')
    title = q.get('title','')[:60]
    has_artifact = pid in art_ids
    already_extracted = pid in ext_ids
    ready = has_artifact and not already_extracted
    status = 'READY' if ready else ('existing' if already_extracted else 'no artifact')
    print(f'  rank={rank:4s} | {status:12s} | {pid[:45]:45s} | {title}')
