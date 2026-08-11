import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv
repo = Path('.')
q = repo / 'outputs/fulltext/acquisition/queue_20260729T182430Z'
_, rows = read_csv(q / 'fulltext_queue.csv')
print(f'Queue: {len(rows)} papers')
for r in rows:
    pid = r['paper_id'][:45]
    title = r.get('title','')[:60]
    print(f'  rank={r["rank"]:4s} | {pid:45s} | {title}')
