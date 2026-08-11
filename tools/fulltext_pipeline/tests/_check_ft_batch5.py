import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

repo = Path('.')
_, ft = read_csv(repo / 'data/curated/screening/full_text_decisions.csv')
_, reg = read_csv(repo / 'data/curated/fulltext/extraction_registry.csv')

target = set(str(i) for i in range(81, 101))

# In FT decisions
ft_ranks = set(r.get('rank','') for r in ft)
overlap = target & ft_ranks
print(f'Already in FT decisions: {len(overlap)}')
if overlap:
    for r in ft:
        if r.get('rank','') in overlap:
            print(f'  rank={r["rank"]:4s} | {r.get("paper_id","")[:45]:45s} | {r.get("decision","")}')

# In extraction registry
reg_ids = set(r.get('paper_id','') for r in reg)
print(f'\nPapers with extraction output:')
_, ta = read_csv(repo / 'data/curated/screening/title_abstract_decisions.csv')
for r in ta:
    if r.get('rank','') in target and r.get('paper_id','') in reg_ids:
        print(f'  rank={r["rank"]:4s} | {r.get("paper_id","")[:45]:45s}')
