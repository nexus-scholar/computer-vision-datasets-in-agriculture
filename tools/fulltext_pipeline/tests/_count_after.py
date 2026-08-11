"""Count screening decisions after adding ranks 43, 47, 70, 71."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ft = read_csv(Path('data/curated/screening/full_text_decisions.csv'))
total = len(ft)
core = sum(1 for d in ft if d.get('decision') == 'include_core')
supp = sum(1 for d in ft if d.get('decision') == 'include_supporting')
unres = sum(1 for d in ft if d.get('decision') == 'unresolved')
excl = sum(1 for d in ft if d.get('decision') == 'exclude')
print(f'Total FT decisions: {total}')
print(f'  include_core: {core}')
print(f'  include_supporting: {supp}')
print(f'  unresolved: {unres}')
print(f'  excluded: {excl}')

# Check review queue for remaining undecided
_, ta = read_csv(Path('data/curated/screening/title_abstract_decisions.csv'))
included = {int(r['rank']) for r in ta if r.get('decision')=='include' and r.get('rank','').isdigit()}
decided = {int(d['rank']) for d in ft if d.get('rank','').isdigit()}
remaining = sorted([r for r in included if r not in decided])
print(f'\nRemaining TA-included without FT decision: {len(remaining)}')
print(f'First 20: {remaining[:20]}')
