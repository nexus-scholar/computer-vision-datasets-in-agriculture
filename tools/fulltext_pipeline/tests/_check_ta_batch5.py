import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv
from collections import Counter

repo = Path('.')
_, ta = read_csv(repo / 'data/curated/screening/title_abstract_decisions.csv')

target = set(str(i) for i in range(81, 101))
rows = [r for r in ta if r.get('rank','') in target]
rows.sort(key=lambda x: int(x.get('rank',0)))

print(f'Ranks 81-100: {len(rows)} TA decisions')
print(f'{"rank":6s} {"decision":20s} {"reason":20s} {"title":60s}')
for r in rows:
    rank = r.get('rank','')
    dec = r.get('decision','')[:18]
    reason = r.get('exclusion_reason','')[:18] if r.get('exclusion_reason') else ''
    title = r.get('title','')[:58]
    print(f'{rank:6s} {dec:20s} {reason:20s} {title:60s}')
