import csv
from pathlib import Path

LEDGER = Path("data/curated/claim_ledger.csv")
SCORES = Path("outputs/dataset_opportunity_scores.csv")

# Verified verdict for every DSO/DT claim against the closed-universe 96-row
# scores file (computed 2026-08-08; see outputs/tmp_check_dso.py).
# superseded: claim text/rank authored against the pre-refresh (30/51-dataset)
#             universe and no longer holds in the closed universe.
VERDICTS = {
    'DSO-001': 'superseded',
    'DSO-002': 'superseded',
    'DSO-003': 'superseded',
    'DSO-004': 'verified',
    'DSO-005': 'superseded',
    'DSO-006': 'verified',
    'DSO-007': 'verified',
    'DSO-008': 'verified',
    'DSO-009': 'verified',
    'DSO-010': 'verified',
    'DSO-011': 'verified',
    'DSO-012': 'verified',
    'DSO-013': 'verified',
    'DSO-014': 'verified',
    'DSO-015': 'verified',
    'DSO-016': 'verified',
    'DSO-017': 'verified',
    'DSO-018': 'verified',
    'DT-003': 'verified',
    'DT-004': 'verified',
    'DT-005': 'verified',
    'DT-006': 'verified',
}

SUPERSEDE_NOTES = {
    'DSO-001': 'SUPERSEDED by DSO-019: ranked 30-dataset universe; in the closed 96-dataset universe AgroVG is rank 2 (22.0) behind MuST-C 24.5, PhenoBench rank 6, AgroTools rank 8.',
    'DSO-002': 'SUPERSEDED by DSO-019: PhenoBench is rank 6 (21.0) in the closed 96-dataset universe, not rank 2.',
    'DSO-003': 'SUPERSEDED by DSO-019: named datasets moved to ranks 11-25 (CropNet 11, WE3DS 16, PLANesT-3D 21, AgriLiRa4D 22, TomatoWUR 23, Crops3D 25). Qualitative conclusion (non-RGB modalities dominate the top) is preserved in DSO-019.',
    'DSO-005': 'SUPERSEDED by DSO-019: ROSE-X is rank 26 (18.5) in the closed universe; top 3D datasets are MaizeField3D (21.5), BonnBeetClouds3D (21.0), Pheno4D (21.0).',
}

NEW_ROW = {
    'claim_id': 'DSO-019',
    'claim_text': ('Closed-universe reconciliation (2026-08-08): verified every DSO/DT claim against the final '
                   '96-row dataset_opportunity_scores.csv. DSO-004 (MuST-C 24.5, rank 1) and DSO-006..DSO-018 '
                   '(Pheno4D 21.0, Two-Season-WeedDet8 20.5, Seedling RGB-depth 20.5, Soybean MVSP2 19.0, '
                   'MaizeField3D 21.5 rank 3, OPPD 21.5 rank 4, BonnBeetClouds3D 21.0 rank 5) verify against '
                   'current totals/ranks; DT-003..DT-006 verified. DSO-001, DSO-002, DSO-003, DSO-005 are '
                   'superseded: their ranks were computed against the pre-refresh 30/51-dataset universes and '
                   'no longer hold. Final top-20: MuST-C 24.5, AgroVG 22.0, MaizeField3D 21.5, OPPD 21.5, '
                   'BonnBeetClouds3D 21.0, PhenoBench 21.0, Pheno4D 21.0, AgroTools 20.5, Two-Season-WeedDet8 '
                   '20.5, Seedling RGB-depth 20.5, CropNet 20.0, IPB Sugar Beets 2016 20.0, LAST-Straw 20.0, '
                   'Broad-Leaf Legumes 20.0, Weeds-Banana 19.5, WE3DS 19.5, TomatoMAP 19.5, MFWD 19.0, GWFSS '
                   '19.0, Soybean MVSP2 19.0.'),
    'scope': 'Reconciliation of all DSO/DT claim-ledger entries against the closed-universe opportunity scores',
    'evidence_ids': 'dataset_opportunity_scores.csv; dataset_registry.csv',
    'evidence_locations': 'outputs/dataset_opportunity_scores.csv (96 rows, ranks 1-96); outputs/tmp_check_dso.py verification run 2026-08-08',
    'contradictory_evidence': '',
    'strength': 'strong',
    'uncertainty': 'low',
    'status': 'proposed',
    'required_validation': 'human: confirm supersession of DSO-001/002/003/005 and the final top-20 list before using it to select experimental-design-gates candidates',
    'reviewer': 'opencode_ai',
    'reviewed_at': '2026-08-08',
    'notes': 'Dataset selection and manuscript claims remain AI-provisional pending human confirmation.',
}


def main():
    with LEDGER.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    changed = []
    for r in rows:
        cid = r['claim_id']
        if cid not in VERDICTS:
            continue
        if VERDICTS[cid] == 'superseded':
            if r['status'] != 'superseded':
                r['status'] = 'superseded'
                r['notes'] = (SUPERSEDE_NOTES[cid] + ' ' + r['notes']).strip()
                changed.append(cid)
        else:
            if r.get('notes', '').startswith('VERIFIED'):
                continue
            r['notes'] = ('VERIFIED against closed-universe 96-row scores (2026-08-08): ' + r['notes']).strip()
            changed.append(cid)

    ids = {r['claim_id'] for r in rows}
    if NEW_ROW['claim_id'] not in ids:
        rows.append({k: NEW_ROW.get(k, '') for k in fieldnames})
        changed.append(NEW_ROW['claim_id'])

    with LEDGER.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f'updated {len(changed)} rows: {changed}')
    print(f'ledger now: {len(rows)} rows')


if __name__ == '__main__':
    main()
