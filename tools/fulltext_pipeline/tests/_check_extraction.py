"""Check extraction results for batch 5."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv
from collections import Counter

repo = Path('.')
_, reg = read_csv(repo / 'data/curated/fulltext/extraction_registry.csv')
_, art = read_csv(repo / 'data/curated/fulltext/artifact_registry.csv')

ranks_processed = ['81','83','84','85','89','90','92','93','94','95','96','98','99','100']
ranks_existing = ['82','86','87','88']
all_ranks = ranks_processed + ranks_existing

# Find latest extraction for each paper
latest = {}
for r in reg:
    pid = r.get('paper_id','')
    if pid not in latest or r.get('created_at','') >= latest[pid].get('created_at',''):
        latest[pid] = r

# Map rank to paper_id from queue
_, queue = read_csv(repo / 'outputs/fulltext/acquisition/queue_20260729T182430Z/fulltext_queue.csv')
rank_to_pid = {q.get('rank',''): q.get('paper_id','') for q in queue}

print('Batch 5 extraction results:')
print(f'{"rank":5s} {"docling":10s} {"grobid":10s} {"xml":10s} {"qa":12s} {"title":55s}')
for rk in all_ranks:
    pid = rank_to_pid.get(rk, '')
    ext = latest.get(pid, {})
    doc = ext.get('docling_status','')[:8]
    gro = ext.get('grobid_status','')[:8]
    xml = ext.get('publisher_xml_status','')[:8]
    qa = ext.get('qa_status','')[:10]
    title = ext.get('title','')[:53]
    print(f'{rk:5s} {doc:10s} {gro:10s} {xml:10s} {qa:12s} {title}')

# Summary
doc_ok = 0
gro_ok = 0
for rk in all_ranks:
    pid = rank_to_pid.get(rk, '')
    ext = latest.get(pid, {})
    if ext.get('docling_status','') == 'success':
        doc_ok += 1
    if ext.get('grobid_status','') == 'success':
        gro_ok += 1
print(f'\nTotal batch 5 papers: {len(all_ranks)}')
print(f'Docling success: {doc_ok}')
print(f'GROBID success: {gro_ok}')
