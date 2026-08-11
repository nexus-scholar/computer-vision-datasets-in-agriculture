"""Show acquisition queue contents."""
import csv
from pathlib import Path

q = sorted(Path('outputs/fulltext/acquisition').glob('queue_*'))[-1] / 'fulltext_queue.csv'
rows = list(csv.DictReader(open(q, encoding='utf-8')))
print(f'Queue: {q}')
print(f'Size: {len(rows)}')
for r in rows:
    rank = r.get('rank','?')
    title = r.get('title','?')[:65]
    pid = r.get('paper_id', r.get('candidate_id','?'))[:55]
    print(f'  {rank:>3s}: {title}')
    print(f'       pid={pid}')
