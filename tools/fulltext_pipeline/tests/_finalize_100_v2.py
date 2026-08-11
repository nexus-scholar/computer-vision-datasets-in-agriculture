"""Generate a properly quoted decision CSV and finalize it."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
import csv

decision_path = Path('outputs/fulltext/reviews/review_0100_20260730T190114Z/decision_template.csv')

fields = [
    'fulltext_screening_id', 'paper_id', 'rank', 'title', 'extraction_id',
    'decision', 'reason_code', 'paper_role', 'actual_dataset_use',
    'dataset_relationship', 'named_datasets', 'evidence_summary',
    'source_page', 'source_section', 'source_table', 'source_figure',
    'reviewer', 'reviewed_at', 'supersedes_fulltext_screening_id', 'notes'
]

row = {
    'fulltext_screening_id': '',
    'paper_id': 'doi:10.1109/aisummit66170.2025.11410995',
    'rank': '100',
    'title': 'SegFormerDiffusion: A Transformer–Diffusion Hybrid for High-Resolution Potato-Leaf Lesion Segmentation',
    'extraction_id': 'FTE_8e76894f1fc6060fa012',
    'decision': 'include_supporting',
    'reason_code': 'FS01_RELEVANT_METHOD',
    'paper_role': 'method_paper',
    'actual_dataset_use': 'yes',
    'dataset_relationship': 'used_training',
    'named_datasets': 'IARI Potato Leaf Dataset (self-collected; 236 images: 150 early blight, 86 healthy)',
    'evidence_summary': 'Self-collected potato leaf disease dataset from IARI used for training SegFormer+Diffusion. Dataset: 236 RGB images (512x512), 2 classes (early blight/healthy), annotated via VIA tool, DSLR camera. 80/20 train/val split; 5-fold CV for ablation. Best: SegFormer(B0)+Diff achieves 99.34% Dice, 98.68% IoU (Table IV). Diffusion decoder improves over UNet decoder (+2.35% Dice, +4.09% IoU) (Table III). No public dataset release. No code release.',
    'source_page': '3,4,5',
    'source_section': 'III-B (Dataset, p3); III-C (Data Preprocessing, p3); IV (Proposed Model, p4); V-A (Implementation, p4); V-B (Ablation Study, p4-5); V-C (Performance Analysis, p5)',
    'source_table': 'Table II (p3, dataset statistics); Table III (p4-5, ablation study); Table IV (p5, performance comparison)',
    'source_figure': 'Figure 1 (p3); Figure 2 (p4); Figure 3 (p5)',
    'reviewer': 'opencode_ai',
    'reviewed_at': '2026-07-30T19:15:00Z',
    'supersedes_fulltext_screening_id': '',
    'notes': 'review_context:outputs/fulltext/reviews/review_0100_20260730T190114Z/review_context.json; docling_failed:std::bad_alloc on 4 of 6 pages; text_extracted_via_pymupdf'
}

with open(decision_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerow(row)

print(f"Written {decision_path.stat().st_size} bytes")

# Now run finalize
from agri_fulltext.cli import main
import sys as _sys
# Can't call main directly, use subprocess
import subprocess
result = subprocess.run([
    _sys.executable, '-m', 'agri_fulltext.cli',
    '--repo', '.',
    'finalize-review',
    str(decision_path)
], capture_output=True, text=True, cwd=Path('.'))
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500] if result.stderr else '')
print("Return code:", result.returncode)
