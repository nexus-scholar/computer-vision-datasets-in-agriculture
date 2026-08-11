"""Get next 20 ranks needing full-text acquisition."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ta = read_csv(Path('data/curated/screening/title_abstract_decisions.csv'))
included = {int(r['rank']): r for r in ta if r.get('decision')=='include' and r.get('rank','').isdigit()}

_, ft = read_csv(Path('data/curated/screening/full_text_decisions.csv'))
decided = {int(d['rank']) for d in ft if d.get('rank','').isdigit()}

remaining = sorted([r for r in included if r not in decided])
batch = remaining[:20]
print(','.join(str(r) for r in batch))
print('\nDetails:')
for r in batch:
    rec = included[r]
    title = rec.get('title','?')[:70]
    print(f'  {r:>3d}: {title}')
