import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

repo = Path('.')
pid = 'doi:10.60507/fk2/ox9xtm'

# Check TA decisions
_, ta = read_csv(repo / 'data/curated/screening/title_abstract_decisions.csv')
for r in ta:
    if r.get('paper_id','') == pid or r.get('rank','') == '91':
        print('=== TA decision ===')
        for k, v in r.items():
            print(f'  {k}: {v}')

# Check priority queue
_, queue = read_csv(repo / 'data/curated/screening/priority_queue.csv')
for r in queue:
    if r.get('rank','') == '91':
        print('\n=== Priority queue ===')
        for k, v in r.items():
            print(f'  {k}: {v}')

# Check FT decisions
_, ft = read_csv(repo / 'data/curated/screening/full_text_decisions.csv')
for r in ft:
    if r.get('paper_id','') == pid or r.get('rank','') == '91':
        print('\n=== FT decision ===')
        for k, v in r.items():
            print(f'  {k}: {v}')
