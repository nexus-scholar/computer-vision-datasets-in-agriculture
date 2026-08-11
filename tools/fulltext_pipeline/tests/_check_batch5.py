"""Check batch 5 (ranks 81-100) status."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ft = read_csv(Path('data/curated/screening/full_text_decisions.csv'))
ft_by_rank = {r.get('rank',''): r for r in ft}

print("Rank 81-100 full-text decision status:")
print(f"{'Rank':<6} {'Decision':<20} {'Paper ID':<50}")
print("-"*80)
for r in range(81, 101):
    key = str(r)
    if key in ft_by_rank:
        d = ft_by_rank[key]
        decision = d.get('decision','?')
        pid = d.get('paper_id','?').split('/')[-1][:45]
        print(f"{r:<6} {decision:<20} {pid}")
    else:
        print(f"{r:<6} {'NO DECISION':<20}")
