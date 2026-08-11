"""Count screening decisions."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

r = Path('.')
_, decisions = read_csv(r / 'data/curated/screening/full_text_decisions.csv')
total = len(decisions)
core = sum(1 for d in decisions if d.get('decision') == 'include_core')
supp = sum(1 for d in decisions if d.get('decision') == 'include_supporting')
unres = sum(1 for d in decisions if d.get('decision') == 'unresolved')
excl = sum(1 for d in decisions if d.get('decision') == 'exclude')
b5 = sum(1 for d in decisions if d.get('rank','').isdigit() and 81 <= int(d['rank']) <= 100)
recent = sum(1 for d in decisions if d.get('reviewed_at','') > '2026-07-28')

print(f"Total decisions: {total}")
print(f"  include_core: {core}")
print(f"  include_supporting: {supp}")
print(f"  unresolved: {unres}")
print(f"  excluded: {excl}")
print(f"  Batch 5 papers: {b5}")
print(f"  Since 2026-07-28: {recent}")
