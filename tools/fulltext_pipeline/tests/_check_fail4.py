"""Check extraction status for ranks 43, 47, 70, 71."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv

_, ext = read_csv(Path('data/curated/fulltext/extraction_registry.csv'))
_, decisions = read_csv(Path('data/curated/screening/full_text_decisions.csv'))
_, ta = read_csv(Path('data/curated/screening/title_abstract_decisions.csv'))

targets = ['43', '47', '70', '71']
print("=== EXTRACTION REGISTRY ===")
for r in ext:
    rank = r.get('rank', '')
    if rank in targets:
        print(f'Rank {rank}: paper_id={r.get("paper_id","")}')
        print(f'   qa={r.get("qa_status","?")} preflight={r.get("preflight_class","?")} created={r.get("created_at","?")}')
        print(f'   output={r.get("output_dir","?")}')

print("\n=== TA DECISIONS ===")
for r in ta:
    rank = r.get('rank', '')
    if rank in targets:
        print(f'Rank {rank}: decision={r.get("decision","?")}')
        print(f'   candidate_id={r.get("candidate_id","?")}')
        print(f'   title={r.get("title","?")}')
        print(f'   full_text={r.get("full_text_available","?")} abstract={r.get("abstract_available","?")}')
        print(f'   doi={r.get("doi","?")}')

print("\n=== FT DECISIONS ===")
for r in decisions:
    rank = r.get('rank', '')
    if rank in targets:
        print(f'Rank {rank}: decision={r.get("decision","?")} paper_id={r.get("paper_id","?")}')
