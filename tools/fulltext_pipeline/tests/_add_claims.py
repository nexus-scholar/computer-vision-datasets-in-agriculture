"""Add batch-5 claim-ledger entries."""
import csv
from pathlib import Path

ledger_path = Path('data/curated/claim_ledger.csv')

with open(ledger_path, 'r', encoding='utf-8') as f:
    existing = list(csv.DictReader(f))

existing_ids = {r['claim_id'] for r in existing}

NEW_CLAIMS = [
    {
        'claim_id': 'DSO-004',
        'claim_text': 'MuST-C is the most opportunity-rich agricultural CV dataset identified, scoring 24.5/25 across all five dimensions due to its multi-sensor (RGB, multispectral, LiDAR), multi-temporal, multi-crop (6 species) design with manual reference measurements.',
        'scope': 'MuST-C dataset (Chong et al., 2025/2026)',
        'evidence_ids': 'doi:10.60507/fk2/ox9xtm',
        'evidence_locations': 'FTS_04adc7b4be8b390c0262; full_text_decisions.csv rank 91',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: verify dataset is publicly accessible and license terms',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-07-30',
        'notes': 'Batch-5 evidence synthesis'
    },
    {
        'claim_id': 'DSO-005',
        'claim_text': 'ROSE-X is the top-ranked 3D agricultural CV dataset with strong baselines (RF, MRF alongside 3D U-Net), suggesting the 3D plant analysis community maintains stronger baseline traditions than RGB agri-CV.',
        'scope': 'ROSE-X dataset',
        'evidence_ids': 'doi:10.1186/s13007-020-00573-w',
        'evidence_locations': 'FTS_6e8c399bcb4af58266ef; full_text_decisions.csv rank 89',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: verify baseline comparison claims from the paper',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-07-30',
        'notes': 'Batch-5 evidence synthesis'
    },
    {
        'claim_id': 'MGA-007',
        'claim_text': 'Multi-sensor datasets (MuST-C, IPB Sugar Beets 2016) are rare but highly valuable for cross-sensor generalization research; less than 16% of 67 papers tested cross-sensor.',
        'scope': 'All 67 method-gap-tagged papers',
        'evidence_ids': 'method_gap_matrix.csv',
        'evidence_locations': 'method_gap_merge.py output; cross_sensor_test column',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: confirm cross-sensor statistics',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-07-30',
        'notes': 'Batch-5 MGA update'
    },
    {
        'claim_id': 'DT-003',
        'claim_text': 'Several open-access agricultural CV datasets from batch 5 (WeedElec-AnnotatedDataset, FruitSeg30, ROSE-X, Latvian Crop-Weed, MuST-C) are CC-BY-4.0 licensed, providing clear reuse pathways for research.',
        'scope': 'Batch-5 dataset papers with CC-BY-4.0',
        'evidence_ids': 'doi:10.1002/aps3.11373; doi:10.1016/j.dib.2024.110821; doi:10.1186/s13007-020-00573-w; doi:10.1016/j.dib.2020.105833; doi:10.60507/fk2/ox9xtm',
        'evidence_locations': 'full_text_decisions.csv ranks 84,85,89,95,91',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: verify licenses on repository pages',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-07-30',
        'notes': 'Batch-5 evidence synthesis'
    },
]

fieldnames = list(existing[0].keys()) if existing else list(NEW_CLAIMS[0].keys())
added = 0
with open(ledger_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in existing:
        w.writerow(r)
    for nc in NEW_CLAIMS:
        if nc['claim_id'] in existing_ids:
            print(f'SKIP (exists): {nc["claim_id"]}')
        else:
            w.writerow(nc)
            added += 1
            print(f'ADDED: {nc["claim_id"]}')

print(f'\nLedger now has {len(existing) + added} rows (+{added} new)')
