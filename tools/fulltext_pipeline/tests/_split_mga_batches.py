"""Split untagged evidence rows into MGA batch CSVs (≤10 papers each)."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
import csv
from agri_fulltext.io_utils import read_csv

# Load existing results to find tagged PIDs
tagged = set()
for p in sorted(Path('outputs').glob('mga_batch_*_results.csv')):
    _, rows = read_csv(p)
    for r in rows:
        pid = r.get('paper_id','').strip()
        if pid:
            tagged.add(pid)

# Load evidence
_, ev = read_csv(Path('outputs/method_gap_evidence.csv'))

# Filter untagged
untagged = [r for r in ev if r.get('paper_id','').strip() not in tagged]
print(f'Untagged: {len(untagged)}')

# Sort by rank
untagged.sort(key=lambda r: int(r.get('rank','999')) if r.get('rank','').isdigit() else 999)

# Split into batches of ≤10
fields = list(ev[0].keys())
batch_size = 7
for i in range(0, len(untagged), batch_size):
    batch_num = i // batch_size + 7  # starting from batch 7
    batch = untagged[i:i+batch_size]
    outpath = Path(f'outputs/mga_batch_{batch_num}_input.csv')
    with open(outpath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in batch:
            w.writerow(row)
    pids = [r['paper_id'] for r in batch]
    ranks = [r.get('rank','?') for r in batch]
    print(f'Batch {batch_num}: {len(batch)} papers, ranks {ranks}')
    for pid in pids:
        print(f'  {pid}')
