import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv
repo = Path('.')
a = repo / 'outputs/fulltext/acquisition/FTA_20260729T182910Z'
print(f'Directory exists: {a.exists()}')
if a.exists():
    for f in sorted(a.iterdir()):
        if f.suffix == '.csv':
            _, rows = read_csv(f)
            print(f'{f.name}: {len(rows)} rows')
        else:
            sz = f.stat().st_size if f.is_file() else 0
            print(f'{f.name} ({sz} bytes)' if f.is_file() else f'{f.name}/')

    # Check manifest
    mf = a / 'acquisition_manifest.json'
    if mf.exists():
        import json
        m = json.loads(mf.read_text())
        status = m.get('status','unknown')
        acquired = m.get('acquired_papers',[])
        failed = m.get('failed_papers',[])
        print(f'\nStatus: {status}')
        print(f'Acquired: {len(acquired)} papers')
        print(f'Failed: {len(failed)} papers')
        for p in failed:
            print(f'  FAILED: {p}')
