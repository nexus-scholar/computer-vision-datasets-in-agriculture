import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv
from collections import Counter
repo = Path('.')
r = repo / 'outputs/fulltext/acquisition/resolution_20260729T182752Z'
_, cand = read_csv(r / 'candidates.csv')
_, queue = read_csv(r / 'fulltext_queue_snapshot.csv')
print(f'Queue: {len(queue)} papers')
print(f'Candidates: {len(cand)} candidate records')
uids = set(c.get('paper_id','') for c in cand)
print(f'Unique paper_ids: {len(uids)}')
sources = Counter(c.get('source','') for c in cand)
print(f'Sources: {dict(sources)}')
scores = Counter(c.get('score','') for c in cand)
print(f'Score readiness: {dict(scores)}')

# Per-paper summary
for c in cand:
    pid = c.get('paper_id','')[:50]
    src = c.get('source','')
    rights = c.get('rights_status','')
    score = c.get('score','')
    print(f'  {pid:50s} | {src:20s} | {rights:20s} | score={score}')
