"""Write rank 70 decision template from agent output."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
import csv

decision_path = Path('outputs/fulltext/reviews/review_0070_20260731T102641Z/decision_template.csv')

fields = [
    'fulltext_screening_id', 'paper_id', 'rank', 'title', 'extraction_id',
    'decision', 'reason_code', 'paper_role', 'actual_dataset_use',
    'dataset_relationship', 'named_datasets', 'evidence_summary',
    'source_page', 'source_section', 'source_table', 'source_figure',
    'reviewer', 'reviewed_at', 'supersedes_fulltext_screening_id', 'notes'
]

row = {
    'fulltext_screening_id': '',
    'paper_id': 'doi:10.1016/j.atech.2026.102373',
    'rank': '70',
    'title': 'Lightweight GSP-YOLO for accurate weed seedling detection and edge deployment in laser-based weed control systems',
    'extraction_id': 'FTE_870dfd8b0a5347978c95',
    'decision': 'include_core',
    'reason_code': 'FI_DATASET',
    'paper_role': 'dataset_paper',
    'actual_dataset_use': 'yes',
    'dataset_relationship': 'introduced',
    'named_datasets': 'NIAM9weeds, Weed25',
    'evidence_summary': 'Introduces NIAM9weeds: 12,200 images of 9 rapeseed-field weed species (COCO format, 640x640, 8:1:1 split -> 9,760/1,220/1,220), collected Mar 2024-Mar 2025 in Anhui/Jiangsu (SONY alpha6000, HONOR Magic4, 25-45 cm) incl. selected public Weed25 data (PDF pp. 12-13, Sec. 3.1-3.2, Table 2, Figs. 9-10). GSP-YOLO (YOLOv8s + GhostNetV3 + SCSA + PIoU) trained/tested on it: 97.74% P / 96.66% R / 98.33% AP, 10-fold CV, ablations, and YOLO-variant comparisons (PDF pp. 15-17, Tables 4-7). Data availability: public HuggingFace URL (PDF p. 28); Sec. 3.1 inconsistently names dataset "Weeds7KPD".',
    'source_page': '13',
    'source_section': '3.1-3.2',
    'source_table': '2',
    'source_figure': '9, 10',
    'reviewer': 'opencode_ai',
    'reviewed_at': '2026-07-31T10:30:00Z',
    'supersedes_fulltext_screening_id': '',
    'notes': 'review workspace: outputs/fulltext/reviews/review_0070_20260731T102641Z; SSRN preprint of doi:10.1016/j.atech.2026.102373; named_datasets includes Weed25 (Wang et al. 2022) incorporated as selected public data'
}

with open(decision_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerow(row)

print(f'Written {decision_path.stat().st_size} bytes')
