import csv
from pathlib import Path

LEDGER = Path("data/curated/claim_ledger.csv")

FIELDS = ['claim_id', 'claim_text', 'scope', 'evidence_ids', 'evidence_locations',
          'contradictory_evidence', 'strength', 'uncertainty', 'status',
          'required_validation', 'reviewer', 'reviewed_at', 'notes']

NEW_ROWS = [
    {
        'claim_id': 'MGA-010',
        'claim_text': ('Across the full 190-paper method-gap matrix, calibration is absent (no) in 189/190 '
                       '(99.5%), same-sensor-only evaluation in 129/190 (67.9%), no code released '
                       '(not_available) in 108/190 (56.8%), random or unclear splits in 177/190 (93.2%), '
                       'and >=4 simultaneous gaps (5-dimension definition from method_gap_merge.py) in '
                       '154/190 (81.1%).'),
        'scope': 'All 190 included full-text papers (150 include_core + 40 include_supporting)',
        'evidence_ids': 'method_gap_matrix.csv',
        'evidence_locations': 'outputs/method_gap_matrix.csv (method_gap_merge.py output; 190 rows, 0 empty cells)',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: confirm tag columns after merge; note legacy tag vocabulary (e.g., available/public, multiple/strong_simple) from batches 1-10 is inconsistent with the batch-11 taxonomy',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-08-08',
        'notes': 'Full-universe MGA re-run (supersedes 94-paper basis in MGA-009; 190 papers tagged). Gap stats via canonical GAP_DIMENSIONS: split random/unclear 177 (93.2%), random 72, unclear 105, grouped 13; baseline sota_only 84, none 61, strong_simple 34; calibration no 189, partial 1; cross-sensor same_sensor 129, cross_dataset 24, cross_sensor 6, both 1, unclear 30; code not_available 108, public 46, not_applicable 36; role introduced 99, used_training 44, unclear 37.',
    },
    {
        'claim_id': 'DSO-016',
        'claim_text': ('MaizeField3D (rank 3, 21.5/25) is the highest-ranked newly introduced batch-8 dataset: '
                       '1,045 TLS point clouds with 520 SAM-panel organ-segmented plants plus procedural NURBS '
                       'models validated through HELIOS canopy PAR simulation (r=0.83), public on Hugging Face '
                       'BGLab/MaizeField3D with subsampled versions, and no published learning baseline.'),
        'scope': 'MaizeField3D dataset (rank 3)',
        'evidence_ids': 'doi:10.31274/td-20260223-107',
        'evidence_locations': 'outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv (rank 3); outputs/dataset_extraction_batch_2_staging.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: verify Hugging Face access and license; confirm no learning baseline exists',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-08-08',
        'notes': 'Batch-8/9 registry-scoring refresh evidence synthesis',
    },
    {
        'claim_id': 'DSO-017',
        'claim_text': ('OPPD (Open Plant Phenotype Database, rank 4, 21.5/25) offers exceptional depth for weed '
                       'CV: 7,590 images, 47 weed species, 315,038 boxes, 64,292 temporally tracked plants, '
                       'and three growth conditions including drought; public access, but only shallow '
                       'two-baseline prior work keeps it below MuST-C.'),
        'scope': 'OPPD dataset (rank 4)',
        'evidence_ids': 'doi:10.3390/rs12081246',
        'evidence_locations': 'outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv (rank 4); outputs/dataset_extraction_batch_2_staging.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: verify public access at vision.eng.au.dk and drought-condition labels',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-08-08',
        'notes': 'Batch-8/9 registry-scoring refresh evidence synthesis',
    },
    {
        'claim_id': 'DSO-018',
        'claim_text': ('BonnBeetClouds3D (rank 5, 21.0/25) is a UAV photogrammetric 3D sugar-beet breeding trial: '
                       '48 varieties, >3,000 plants, 186 annotated plants, 2,661 leaf instances, >10,000 '
                       'keypoints, expert trait references, and a clean train/val/test leaf split, hosted at '
                       'bonnbeetclouds3d.ipb.uni-bonn.de.'),
        'scope': 'BonnBeetClouds3D dataset (rank 5)',
        'evidence_ids': 'doi:10.1109/iros58592.2024.10802820',
        'evidence_locations': 'outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv (rank 5); outputs/dataset_extraction_batch_2_staging.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm access/license at the project site and leaf-split details',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-08-08',
        'notes': 'Batch-8/9 registry-scoring refresh evidence synthesis',
    },
    {
        'claim_id': 'DT-006',
        'claim_text': ('The dataset registry and opportunity scores were refreshed to the closed 190-paper '
                       'screening universe: registry now has 96 unique datasets (2 batch-8 duplicates merged: '
                       'PLANesT-3D, TomatoWUR), scores have 96 rows with contiguous ranks 1-96, and 3 papers '
                       'whose scores were lost in a name-keyed merge were re-scored from MGA evidence '
                       '(Ara2012/Ara2013/Tobacco CVPPP rank 80, WA multispectral weed rank 30, Synthetic apple '
                       'orchard rank 60).'),
        'scope': 'Dataset registry and opportunity-score refresh (batch 7/8 additions, closed universe)',
        'evidence_ids': 'dataset_registry.csv; dataset_opportunity_scores.csv; dataset_registry_dedup_audit.json',
        'evidence_locations': 'outputs/dataset_registry.csv (96 rows); outputs/dataset_opportunity_scores.csv (96 rows); outputs/dataset_registry_dedup_audit.json; outputs/dataset_scoring_batch_rescore_staging.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm the 2 dataset merges (canonical introducing paper retained) and the 3 re-scored entries',
        'reviewer': 'opencode_ai',
        'reviewed_at': '2026-08-08',
        'notes': 'Registry/scoring refresh completion; prior 51-dataset baseline superseded by 96-dataset universe.',
    },
    {
        'claim_id': 'DT-007',
        'claim_text': ('Batch 7 (final current state, supersedes DT-005) = 7 include (ranks 139, 149, 150, 155, '
                       '212, 268, 334) + 12 unresolved. Rank 184 (TomatoMAP) was recovered from a user-supplied '
                       'PDF and finalized include_core FI01 (FTS_639cf9461904678ed830, extraction '
                       'FTE_779656a9f17c774ecc9e, reviewed 2026-08-08), superseding the stale FU1 '
                       '(FTS_b5e2c2ba51e32e54f383). The remaining 12 ranks (52, 62, 78, 103, 105, 106, 109, '
                       '114, 117, 145, 188, 278) remain unresolved FU1 with empty extraction_id.'),
        'scope': 'Full-text screening, batch 7 (current state)',
        'evidence_ids': 'full_text_decisions.csv',
        'evidence_locations': 'data/curated/screening/full_text_decisions.csv ranks 52,62,78,103,105,106,109,114,117,139,145,149,150,155,184,188,212,268,278,334; outputs/fulltext/acquisition/FTA_20260803T005806Z/summary.csv',
        'contradictory_evidence': 'DT-005 (superseded: counted 13 unresolved)',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'supported',
        'required_validation': 'none - human-audited 2026-08-11 (AUDIT_20260811210101328482); no further action unless user supplies PDFs for the 12 FU1 ranks',
        'reviewer': 'USER',
        'reviewed_at': '2026-08-11',
        'notes': 'Supersedes DT-005 per human audit AUDIT_20260811210101328482. 7-include list and lawful-acquisition-failure finding from DT-005 stand; count corrected from 13 to 12 unresolved.',
    },
    {
        'claim_id': 'MGA-011',
        'claim_text': ('Across the current 194-paper method-gap matrix (supersedes MGA-010, 190-paper basis), '
                       'calibration is absent (no) in 193/194 (99.5%), same-sensor-only evaluation in 132/194 '
                       '(68.0%), no code released (not_available) in 111/194 (57.2%), and >=4 simultaneous gaps '
                       '(5-dimension definition from method_gap_merge.py GAP_DIMENSIONS) in 157/194 (80.9%). '
                       'All 6 tag columns have 0 empty cells.'),
        'scope': 'All 194 included full-text papers (153 include_core + 41 include_supporting)',
        'evidence_ids': 'method_gap_matrix.csv',
        'evidence_locations': 'outputs/method_gap_matrix.csv (method_gap_merge.py output; 194 rows, 0 empty cells)',
        'contradictory_evidence': 'MGA-009 (superseded: 94-paper basis); MGA-010 (superseded as basis: 190-paper basis)',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'supported',
        'required_validation': 'none - figures human-recomputed 2026-08-11 (AUDIT_20260811214039230608); legacy tag vocabulary from batches 1-10 remains inconsistent with the batch-11 taxonomy',
        'reviewer': 'USER',
        'reviewed_at': '2026-08-11',
        'notes': 'Full-universe MGA re-run (supersedes 190-paper MGA-010 basis; 194 papers tagged 2026-08-11 after finalizing 4 recovered IEEE papers - 3 core + 1 supporting). Gap stats via canonical 5-dim GAP_DIMENSIONS: split random 74, unclear 106, grouped 14; baseline sota_only 86, none 62, strong_simple 35, unclear 11; calibration no 193, yes 1; cross_sensor same 132, cross_dataset 25, cross_sensor 6, both 1, unclear 30; code not_available 111, public 47, not_applicable 36; role introduced 99, used_training 47, used_evaluation 8, benchmarked 2, extended 1, unclear 37.',
    },
]


def main():
    with LEDGER.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        existing = list(reader)
        fieldnames = reader.fieldnames
    existing_ids = {r['claim_id'] for r in existing}
    added = []
    for row in NEW_ROWS:
        if row['claim_id'] in existing_ids:
            print(f"SKIP (exists): {row['claim_id']}")
            continue
        existing.append({k: row.get(k, '') for k in fieldnames})
        added.append(row['claim_id'])
    with LEDGER.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing)
    print(f'appended {len(added)} rows: {added}')
    print(f'ledger now: {len(existing)} rows')


if __name__ == '__main__':
    main()
