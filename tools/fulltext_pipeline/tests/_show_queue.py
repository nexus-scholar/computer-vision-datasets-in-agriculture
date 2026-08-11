"""Show next batch of review queue."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

queues = sorted(Path('outputs/fulltext').glob('review_queue_*'))
latest = queues[-1] / 'fulltext_review_queue.csv'
_, rows = read_csv(latest)
print(f'Queue: {latest}')
print(f'Total: {len(rows)} papers')
print('Top 20 by rank:')
for r in rows[:20]:
    rank = r.get('rank', '?')
    title = r.get('title', '?')[:80]
    print(f'  Rank {rank:>3s}: {title}')
