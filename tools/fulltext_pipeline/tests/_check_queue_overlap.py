"""Compare review queue vs full-text decisions."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

# Full-text decisions
_, ft = read_csv(Path('data/curated/screening/full_text_decisions.csv'))
ft_pids = {r.get('paper_id','').strip() for r in ft}

# Review queue
queues = sorted(Path('outputs/fulltext').glob('review_queue_*'))
latest = queues[-1] / 'fulltext_review_queue.csv'
_, q = read_csv(latest)

print(f'Queue: {len(q)} papers')
print(f'Full-text decisions: {len(ft_pids)} pids')

# Count overlaps
in_both = 0
for r in q:
    pid = r.get('paper_id','').strip()
    if pid in ft_pids:
        in_both += 1

print(f'Papers in queue that already have full-text decisions: {in_both}')

# Show the first few that overlap
for r in q[:30]:
    pid = r.get('paper_id','').strip()
    rank = r.get('rank','?')
    title = r.get('title','?')
    already = ' (HAS FT)' if pid in ft_pids else ''
    print(f'  Rank {rank:>3s}: {already} {title[:60]}')

# Next 10 without decisions
print('\nFirst 10 without decisions:')
count = 0
for r in q:
    pid = r.get('paper_id','').strip()
    if pid not in ft_pids:
        rank = r.get('rank','?')
        title = r.get('title','?')
        print(f'  Rank {rank:>3s}: {title[:70]}')
        count += 1
        if count >= 10:
            break
