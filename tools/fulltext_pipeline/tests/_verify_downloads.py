"""Verify first-page metadata of 4 downloaded PDFs against intended papers."""
import hashlib
from pathlib import Path
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not available")
    sys.exit(1)

downloads = Path.home() / 'Downloads'
files = {
    'rank43_atech_2025_101020': downloads / '1-s2.0-S2772375525002539-main.pdf',
    'rank47_compag_2024_109607': downloads / '1-s2.0-S0168169924009980-main.pdf',
    'rank71_inmateh_78_50': downloads / '78-50-N1839-Yang-RAN6f857b77-3ef7-4764-b3a6-5b639c78e342.pdf',
    'rank70_ssrn': downloads / 'ssrn-6881559.pdf',
}

for label, p in files.items():
    if not p.exists():
        print(f'{label}: MISSING {p}')
        continue
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    doc = fitz.open(p)
    first = doc[0].get_text()[:600]
    print(f'=== {label} ===')
    print(f'  size={p.stat().st_size} pages={doc.page_count} sha256={sha[:16]}')
    print('  first-page text:')
    for line in first.split('\n')[:8]:
        clean = line.strip().encode('ascii', 'replace').decode()
        print(f'    {clean[:90]}')
    print()
    doc.close()
