"""Check fetch attempts for ranks 43, 47, 70, 71."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, attempts = read_csv(Path('data/curated/fulltext/fetch_attempt_registry.csv'))
targets = ['doi:10.1016/j.atech.2025.101020', 'doi:10.1016/j.compag.2024.109607',
           'doi:10.1016/j.atech.2026.102373', 'doi:10.35633/inmateh-78-50']
for a in attempts:
    pid = a.get('paper_id', '')
    if pid in targets:
        print(f'{pid}')
        print(f'   status={a.get("status","?")} provider={a.get("provider","?")} url={a.get("url","?")[:80]}')
        print(f'   error={a.get("error","")[:120]} at={a.get("attempted_at","?")}')
