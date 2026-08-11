"""Verify 10 user-downloaded PDFs against intended seed papers (first-page identity)."""
import sys, io, hashlib, json, csv, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path

PDFS = {
    'C:/Users/mouadh/Downloads/electronics-14-04082.pdf': '6',
    'C:/Users/mouadh/Downloads/robotics-15-00081-v2.pdf': '11',
    'C:/Users/mouadh/Downloads/fsufs-10-1841305.pdf': '14',
    'C:/Users/mouadh/Downloads/applsci-16-03745-v2.pdf': '17',
    'C:/Users/mouadh/Downloads/1-s2.0-S1537511025000832-main.pdf': '28',
    'C:/Users/mouadh/Downloads/agronomy-15-01954.pdf': '31',
    'C:/Users/mouadh/Downloads/Advanced_Plant_Disease_Segmentation_in_Precision_Agriculture_Using_Optimal_Dimensionality_Reduction_With_Fuzzy_C-Means_Clustering_and_Deep_Learning.pdf': '35',
    'C:/Users/mouadh/Downloads/1-s2.0-S1574954124000888-main.pdf': '38',
    'C:/Users/mouadh/Downloads/remotesensing-16-04394-v2.pdf': '39',
    'C:/Users/mouadh/Downloads/agriculture-16-00215-v2.pdf': '41',
}

# Expected titles from screening decisions
dec = {}
for r in csv.DictReader(open('data/curated/screening/full_text_decisions.csv', encoding='utf-8')):
    dec[r['rank']] = r['title']

for path, rank in PDFS.items():
    p = Path(path)
    if not p.exists():
        print(f'[missing] rank {rank}: {path}')
        continue
    data = p.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    try:
        import fitz
        doc = fitz.open(path)
        pages = doc.page_count
        first = doc[0].get_text()[:300].replace('\n', ' | ')
        doc.close()
    except Exception as e:
        pages, first = '?', f'ERROR {e}'
    exp = (dec.get(rank) or '')[:80]
    print(f'rank={rank}')
    print(f'  file: {p.name} ({p.stat().st_size} bytes, {pages}pp, sha256={sha[:16]}...)')
    print(f'  expect: {exp}')
    print(f'  first:  {first[:180]}')
    print()
