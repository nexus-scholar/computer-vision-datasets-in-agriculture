"""Copy MuST-C PDF from Downloads to project raw dir."""
import shutil
from pathlib import Path

src = Path.home() / 'Downloads' / 's41597-025-06462-y_reference.pdf'
dst = Path(r'C:\Users\mouadh\Documents\Computer Vision Datasets in Agriculture\data\raw\fulltext\rank_91_MuST-C.pdf')

if not src.exists():
    print(f'Source not found: {src}')
    # Try alternate names
    for f in Path.home().glob('Downloads/*41597*06462*'):
        print(f'Found: {f}')
        src = f
        break

if src.exists():
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f'Copied {src} -> {dst}')
    print(f'Size: {dst.stat().st_size} bytes')
else:
    print('ERROR: Source PDF not found')
