"""Check paper.md files in the new processing run."""
from pathlib import Path

base = Path(r'C:\Users\mouadh\Documents\Computer Vision Datasets in Agriculture\outputs\fulltext\processing\FTP_20260731T095335Z')
for sub in sorted(base.iterdir()):
    if not sub.is_dir():
        continue
    llm = sub / 'llm'
    if llm.exists():
        for f in llm.iterdir():
            print(f'{sub.name}: {f.name} size={f.stat().st_size}')
    else:
        print(f'{sub.name}: NO llm/ dir')
    manifest = sub / 'manifest.json'
    if manifest.exists():
        import json
        d = json.loads(manifest.read_text(encoding='utf-8'))
        print(f'   status={d.get("status")} qa={d.get("qa_status")}')
