import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

repo = Path('.')
pid = 'doi:10.1038/s41597-025-06462-y'
_, ta = read_csv(repo / 'data/curated/screening/title_abstract_decisions.csv')
_, queue = read_csv(repo / 'data/curated/screening/priority_queue.csv')

for r in ta:
    if r.get('paper_id','') == pid or pid in r.get('paper_id',''):
        print('=== TA decision ===')
        print(f'  rank: {r.get("rank","")}')
        print(f'  title: {r.get("title","")}')
        print(f'  decision: {r.get("decision","")}')
        break
else:
    print('Not found in TA decisions')

for r in queue:
    if r.get('canonical_paper_id','') == pid:
        print('=== In queue ===')
        print(f'  rank: {r.get("rank","")}')
        break
else:
    print('Not found in priority queue')
