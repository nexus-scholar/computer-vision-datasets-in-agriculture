"""Fill and finalize rank 91 (MuST-C) review decision."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
import csv
import subprocess

decision_path = Path('outputs/fulltext/reviews/review_0091_20260730T211428Z/decision_template.csv')

fields = [
    'fulltext_screening_id', 'paper_id', 'rank', 'title', 'extraction_id',
    'decision', 'reason_code', 'paper_role', 'actual_dataset_use',
    'dataset_relationship', 'named_datasets', 'evidence_summary',
    'source_page', 'source_section', 'source_table', 'source_figure',
    'reviewer', 'reviewed_at', 'supersedes_fulltext_screening_id', 'notes'
]

row = {
    'fulltext_screening_id': '',
    'paper_id': 'doi:10.60507/fk2/ox9xtm',
    'rank': '91',
    'title': 'MuST-C Dataset: The Multi-Sensor and Multi-Temporal Data Set of Multiple Crops for In-Field Phenotyping and Monitoring',
    'extraction_id': 'FTE_e059aa8430eb59229da6',
    'decision': 'include_core',
    'reason_code': 'FI01_INTRODUCES_DATASET',
    'paper_role': 'dataset_paper',
    'actual_dataset_use': 'yes',
    'dataset_relationship': 'introduced',
    'named_datasets': 'MuST-C (Multi-Sensor, multi-Temporal, multiple Crops)',
    'evidence_summary': 'Introduces MuST-C, a multi-sensor multi-temporal crop phenotyping dataset. Six crop species (sugar beet, maize, wheat, potato, soybean, intercrops). Sensors: UAV RGB (DJI M600/PhaseOne iXM-100), multispectral (MicaSense RedEdge-MX), LiDAR (Velodyne VLP-16), ground robot RGB (Basler) + LiDAR (Velodyne VLP-16). Manual LAI (SunScan/LAI-2200C) and biomass reference measurements. CC BY 4.0 license on bonndata (doi:10.60507/FK2/OX9XTM). GitHub code repo (github.com/PRBonn/MuST-C) with processing tools.',
    'source_page': '1-15',
    'source_section': 'Abstract (p1); Background (p2-4); Methods (p4-10); Data Records (p10-11); Technical Validation (p11-13); Usage Notes (p13-14)',
    'source_table': 'Table 1 (crop field details); Table 2 (sensor specs); Table 3 (flight specs); Table 4-5 (collection dates); Table 6 (dataset structure)',
    'source_figure': 'Figure 1 (sensor platforms); Figure 2 (field layout); Figure 3-4 (example data); Figure 5-7 (validation results)',
    'reviewer': 'opencode_ai',
    'reviewed_at': '2026-07-30T21:20:00Z',
    'supersedes_fulltext_screening_id': '',
    'notes': 'review_context:outputs/fulltext/reviews/review_0091_20260730T211428Z/review_context.json; user_supplied_pdf'
}

with open(decision_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerow(row)

print(f'Written {decision_path.stat().st_size} bytes')

result = subprocess.run([
    sys.executable, '-m', 'agri_fulltext.cli',
    '--repo', '.',
    'finalize-review',
    str(decision_path)
], capture_output=True, text=True, cwd=Path('.'))
print('STDOUT:', result.stdout)
if result.stderr:
    print('STDERR:', result.stderr[:500])
print('Return code:', result.returncode)
