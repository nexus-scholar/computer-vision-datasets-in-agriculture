"""Find papers in queue that need full-text review."""
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

new = [r for r in q if r.get('paper_id','').strip() not in ft_pids]
print(f'Papers awaiting full-text review: {len(new)}')
for r in sorted(new, key=lambda x: int(x.get('rank','999'))):
    pid = r.get('paper_id','').strip()
    rank = r.get('rank','?')
    title = r.get('title','?')
    qa = r.get('qa_status','?')
    print(f'  Rank {rank:>3s} [{qa}] {title[:70]}')
    print(f'        pid={pid}')
