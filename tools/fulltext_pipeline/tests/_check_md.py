"""Check paper.md availability for untagged papers."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ev = read_csv(Path('outputs/method_gap_evidence.csv'))

tagged = set()
for p in Path('outputs').glob('mga_batch_*_results.csv'):
    _, rows = read_csv(p)
    for r in rows:
        pid = r.get('paper_id','').strip()
        if pid:
            tagged.add(pid)

untagged = [r for r in ev if r.get('paper_id','').strip() not in tagged]

for r in untagged:
    md = r.get('paper_md_path', '')
    pid = r.get('paper_id', '')
    rank = r.get('rank', '?')
    short_pid = pid.split('/')[-1][:50] if pid else '?'
    if md:
        p = Path(md)
        exists = p.exists()
        size = p.stat().st_size if exists else 0
    else:
        exists = False
        size = 0
    print(f'Rank {rank:>3s}: pid={short_pid:50s} md_exists={exists} size={size}')
