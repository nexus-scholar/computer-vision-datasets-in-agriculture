"""Check extraction registry for rank 91 related DOIs."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ext = read_csv(Path('data/curated/fulltext/extraction_registry.csv'))
for r in ext:
    pid = r.get('paper_id','')
    rank = r.get('rank','')
    if 'ox9xtm' in pid or '06462' in pid or rank == '91':
        print(f'Rank {rank}: pid={pid}, qa={r.get("qa_status")}, output={r.get("output_dir")}')
