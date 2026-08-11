"""Verify evidence synthesis state."""
import csv
from pathlib import Path

r = list(csv.DictReader(open(Path('outputs/dataset_registry.csv'), encoding='utf-8')))
s = list(csv.DictReader(open(Path('outputs/dataset_opportunity_scores.csv'), encoding='utf-8')))
l = list(csv.DictReader(open(Path('data/curated/claim_ledger.csv'), encoding='utf-8')))

print(f'Registry: {len(r)} rows')
print(f'Scores: {len(s)} rows')
print(f'Ledger: {len(l)} rows')

print('\nTop 10 by opportunity score:')
s_sorted = sorted(s, key=lambda x: float(x.get('total',0) or 0), reverse=True)
for i, row in enumerate(s_sorted[:10]):
    name = row['dataset_name'][:50]
    total = row['total']
    print(f'  {i+1:2d}. {name:50s} total={total}')
