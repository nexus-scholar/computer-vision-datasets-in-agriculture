"""Get dataset relationships from batch 5 decisions."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ft = read_csv(Path('data/curated/screening/full_text_decisions.csv'))
print(f"{'Rank':<6} {'Decision':<18} {'DatasetRel':<18} {'ActualUse':<10} {'NamedDatasets'}")
print("-"*120)
for r in ft:
    rank = r.get('rank','')
    if rank.isdigit() and 81 <= int(rank) <= 100:
        print(f"{rank:<6} {r.get('decision','?'):<18} {r.get('dataset_relationship','?'):<18} {r.get('actual_dataset_use','?'):<10} {r.get('named_datasets','?')[:60]}")
