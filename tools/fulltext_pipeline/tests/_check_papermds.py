"""Check which batch 5 papers have paper.md available."""
from pathlib import Path
repo = Path('.')

# Map ranks to processing directories
dirs = {
    '81': 'doi_10.3390_s23010065',
    '83': 'doi_10.1016_j.ophoto.2024.100078',
    '84': 'doi_10.1002_aps3.11373',
    '85': 'doi_10.1016_j.dib.2024.110821',
    '89': 'doi_10.1186_s13007-020-00573-w',
    '90': 'doi_10.1016_j.knosys.2024.112655',
    '92': 'doi_10.48550_arxiv.2503.05568',
    '93': 'doi_10.1109_wacv.2014.6835733',
    '94': 'doi_10.1371_journal.pone.0077151',
    '95': 'doi_10.1016_j.dib.2020.105833',
    '96': 'doi_10.1177_0278364917720510',
    '98': 'doi_10.3390_agronomy16050536',
    '99': 'doi_10.18420_giljt2025_02',
    '100': 'doi_10.1109_aisummit66170.2025.11410995',
}

base = repo / 'outputs/fulltext/processing/FTP_20260730T160041Z'
print('Papers with extracted content:')
for rank, dname in sorted(dirs.items()):
    pmd = base / dname / 'llm' / 'paper.md'
    mf = base / dname / 'manifest.json'
    has_md = pmd.exists()
    md_size = pmd.stat().st_size if has_md else 0
    
    import json
    m = json.loads(mf.read_text()) if mf.exists() else {}
    px = m.get('publisher_xml',{}).get('status','')
    
    status = 'OK' if has_md and md_size > 100 else 'EMPTY' if has_md else 'NO'
    source = f'xml={px}' if px else 'none'
    print(f'  rank={rank:4s} | {status:5s} | {md_size:8d} bytes | {source} | {dname[:50]}')
