"""Finalize batch-6 evidence synthesis.

Appends 5 newly introduced datasets to the dataset registry, re-ranks
opportunity scores deterministically, and appends claim-ledger entries.

Idempotent: skips rows whose (paper_id, dataset_name) or claim_id already exist.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, 'tools/fulltext_pipeline/src')

REVIEWED_AT = '2026-08-02'

NEW_REGISTRY = [
    {
        'paper_id': 'doi:10.1371/journal.pone.0256340',
        'dataset_name': 'Pheno4D',
        'crop': 'maize, tomato',
        'task': 'instance segmentation, semantic segmentation, 3D reconstruction, non-rigid registration, plant phenotyping',
        'modality': '3D point clouds (laser scanning)',
        'platform': 'laser scanner (high-frequency, high-precision)',
        'image_count': '126 labeled point clouds (49 maize + 77 tomato), ~260M labeled points; 140 tomato plants total (~350M points)',
        'license': 'CC-BY-4.0',
        'access_url': 'https://www.ipb.uni-bonn.de/data/pheno4d/',
        'annotation_type': 'point-level semantic labels, instance labels (Leaf Label / Leaf Tip methods)',
        'notes': 'Multi-temporal spatio-temporal dataset (plants scanned on different days); public with Python/C++ API; Free_model row rank 34.',
    },
    {
        'paper_id': 'doi:10.3390/electronics14204082',
        'dataset_name': 'AgriAdapt',
        'crop': 'salad crops, weeds',
        'task': 'semantic segmentation (crop vs weed), real-time weed detection',
        'modality': 'RGB (UAV)',
        'platform': 'low-cost UAV (Arducam IMX519 RGB camera)',
        'image_count': '643 (text) / 747 (abstract) high-resolution aerial images (discrepancy); 1280x1280, GSD 0.4 cm/px; 322 Field_ID_1 + 321 Field_ID_2',
        'license': 'CC-BY-4.0',
        'access_url': 'https://app.roboflow.com/agriadaptweeddetection/agriadapt-uex2n/overview',
        'annotation_type': 'pixel-level masks (YOLOv7 PyTorch format), crop/weed classes',
        'notes': 'Two fields in Rome, Italy; on-board real-time detection; text vs abstract image-count inconsistency (643 vs 747) flagged.',
    },
    {
        'paper_id': 'doi:10.1016/j.ecoinf.2024.102546',
        'dataset_name': 'Two-Season-WeedDet8',
        'crop': '8 weed species',
        'task': 'object detection, cross-season generalization',
        'modality': 'RGB',
        'platform': 'hand-held color cameras',
        'image_count': '6,664 images, 10,848 bounding boxes (2021: 4,734 imgs/7,664 bbox; 2022: 1,930 imgs/3,184 bbox)',
        'license': 'CC-BY-NC-ND-4.0',
        'access_url': 'https://doi.org/10.5281/zenodo.10762138',
        'annotation_type': 'bounding boxes',
        'notes': 'Two seasons 2021+2022; 2021 subset from CottonWeedDet12; GitHub CrossSeasonWeedDetection; cross-season detection benchmark.',
    },
    {
        'paper_id': 'doi:10.3390/rs16234394',
        'dataset_name': 'Bean Soy dataset',
        'crop': 'bean (Phaseolus vulgaris), soybean (Glycine max), weeds',
        'task': 'object detection, instance segmentation, semantic segmentation',
        'modality': 'RGB (UAV)',
        'platform': 'DJI Phantom 3 Standard UAV (RGB Full HD 1920x1080)',
        'image_count': '793 original images (16,113 instances); augmented to 3,021 (2,270 train / 370 val / 381 test)',
        'license': 'CC-BY-4.0',
        'access_url': 'not specified (available on request)',
        'annotation_type': 'bounding boxes (3 classes: bean, soybean, weed); Roboflow',
        'notes': 'Acquired Dec 2022-Feb 2023 at Goiano Federal Institute-Campus Ceres, Brazil; random split; 8.92 avg weeds/picture; Data Availability on request despite abstract implying public access.',
    },
    {
        'paper_id': 'doi:10.3390/agriculture16020215',
        'dataset_name': '3D Rice WBPH Damage',
        'crop': 'rice (15 materials, 3 replicates each, 45 pots)',
        'task': 'semantic segmentation (background, healthy, damaged), damage severity/resistance evaluation',
        'modality': '3D point clouds (SfM/MVS from multi-view RGB video)',
        'platform': 'Huawei Mate60 Pro (video) + COLMAP reconstruction; CloudCompare annotation',
        'image_count': '174 point clouds (194,395,259 points); 129 train / 45 test',
        'license': 'CC-BY-4.0',
        'access_url': 'not specified (available on request)',
        'annotation_type': 'point-level semantic labels (background, healthy, damaged)',
        'notes': 'Test set = final collection of each pot (grouped split by pot); baselines PointNet/PointNet++/ShellNet/PointCNN; Data Availability on request.',
    },
]

NEW_SCORES = [
    {
        'paper_id': 'doi:10.1371/journal.pone.0256340',
        'dataset_name': 'Pheno4D',
        'modality': '3D point clouds (laser scanning)',
        'task': 'instance segmentation, semantic segmentation, 3D reconstruction, registration',
        'data_richness': '4.5',
        'underuse': '3.5',
        'novelty_fit': '4.5',
        'feasibility': '4.5',
        'publication_leverage': '4.0',
        'notes': 'Multi-temporal spatio-temporal 3D, ~260M labeled points, semantic+instance labels, 2 crops; public with API; underused vs RGB.',
    },
    {
        'paper_id': 'doi:10.1016/j.ecoinf.2024.102546',
        'dataset_name': 'Two-Season-WeedDet8',
        'modality': 'RGB',
        'task': 'object detection, cross-season generalization',
        'data_richness': '3.5',
        'underuse': '4.5',
        'novelty_fit': '4.5',
        'feasibility': '4.5',
        'publication_leverage': '3.5',
        'notes': 'Two-season temporal structure = built-in domain shift; public Zenodo + GitHub; 8 weed classes.',
    },
    {
        'paper_id': 'doi:10.3390/electronics14204082',
        'dataset_name': 'AgriAdapt',
        'modality': 'RGB (UAV)',
        'task': 'semantic segmentation (crop vs weed), real-time detection',
        'data_richness': '3.0',
        'underuse': '4.5',
        'novelty_fit': '3.5',
        'feasibility': '4.5',
        'publication_leverage': '3.0',
        'notes': 'New public low-cost UAV RGB dataset on Roboflow; image-count inconsistency (643 vs 747) is a quality risk.',
    },
    {
        'paper_id': 'doi:10.3390/agriculture16020215',
        'dataset_name': '3D Rice WBPH Damage',
        'modality': '3D point clouds (SfM/MVS)',
        'task': 'semantic segmentation, damage severity/resistance evaluation',
        'data_richness': '3.5',
        'underuse': '4.5',
        'novelty_fit': '4.5',
        'feasibility': '2.0',
        'publication_leverage': '3.5',
        'notes': '3D insect-damage dataset with grouped pot-level split; request-only access lowers feasibility.',
    },
    {
        'paper_id': 'doi:10.3390/rs16234394',
        'dataset_name': 'Bean Soy dataset',
        'modality': 'RGB (UAV)',
        'task': 'object detection, instance segmentation, semantic segmentation',
        'data_richness': '3.0',
        'underuse': '4.0',
        'novelty_fit': '3.0',
        'feasibility': '2.5',
        'publication_leverage': '3.0',
        'notes': 'Random split, single site; Data Availability on request despite abstract implying public access.',
    },
]

NEW_CLAIMS = [
    {
        'claim_id': 'DSO-006',
        'claim_text': 'Pheno4D is the highest-ranked newly introduced batch-6 3D dataset (21.0/25), driven by multi-temporal spatio-temporal structure, ~260M labeled points, semantic+instance labels, and public access with API.',
        'scope': 'Pheno4D dataset (rank 34)',
        'evidence_ids': 'doi:10.1371/journal.pone.0256340',
        'evidence_locations': 'FTS_aaf478680c0b206488c9; full_text_decisions.csv rank 34; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: verify dataset license and public access; confirm instance-label quality on the site',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 evidence synthesis'
    },
    {
        'claim_id': 'DSO-007',
        'claim_text': 'Two-Season-WeedDet8 is the top-ranked newly introduced batch-6 RGB dataset (20.5/25) because its two-season structure provides a built-in temporal domain-shift benchmark for cross-season weed detection.',
        'scope': 'Two-Season-WeedDet8 dataset (rank 38)',
        'evidence_ids': 'doi:10.1016/j.ecoinf.2024.102546',
        'evidence_locations': 'FTS_be6e72f36411dccb2939; full_text_decisions.csv rank 38; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm Zenodo license (CC-BY-NC-ND-4.0) permits intended reuse',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 evidence synthesis'
    },
    {
        'claim_id': 'DSO-008',
        'claim_text': 'AgriAdapt (rank 6) introduces a public low-cost UAV RGB dataset but has a material quality risk: the text states 643 images while the abstract states 747, an unresolved inconsistency.',
        'scope': 'AgriAdapt dataset (rank 6)',
        'evidence_ids': 'doi:10.3390/electronics14204082',
        'evidence_locations': 'FTS_1bb855e38cdaaca7883d; full_text_decisions.csv rank 6; outputs/dataset_registry.csv',
        'contradictory_evidence': '',
        'strength': 'weak',
        'uncertainty': 'high',
        'status': 'proposed',
        'required_validation': 'human: reconcile image count (643 vs 747) against the Roboflow repository',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 evidence synthesis'
    },
    {
        'claim_id': 'DSO-009',
        'claim_text': '3D Rice WBPH Damage (rank 41) is a novel 3D insect-damage dataset with a grouped pot-level test split, but request-only access makes it low-feasibility (2.0/5) for independent reproduction.',
        'scope': '3D Rice WBPH Damage dataset (rank 41)',
        'evidence_ids': 'doi:10.3390/agriculture16020215',
        'evidence_locations': 'FTS_0764f39cd1bb37750d37; full_text_decisions.csv rank 41; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm data-on-request availability and license terms',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 evidence synthesis'
    },
    {
        'claim_id': 'DSO-010',
        'claim_text': 'Bean Soy dataset (rank 39) has an access-contract inconsistency: the abstract implies public availability while the Data Availability statement says on request, which lowers its feasibility score (2.5/5).',
        'scope': 'Bean Soy dataset (rank 39)',
        'evidence_ids': 'doi:10.3390/rs16234394',
        'evidence_locations': 'FTS_a11a0b6d3c4c7c3c9219; full_text_decisions.csv rank 39; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'weak',
        'uncertainty': 'high',
        'status': 'proposed',
        'required_validation': 'human: verify actual public availability',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 evidence synthesis'
    },
    {
        'claim_id': 'MGA-008',
        'claim_text': 'Across the expanded 87-paper method-gap matrix, calibration is absent in 79/87 (90.8%), same-sensor evaluation in 59/87 (67.8%), no code released in 50/87 (57.5%), and >=4 simultaneous gaps in 63/87 (72.4%).',
        'scope': 'All 87 method-gap-tagged papers',
        'evidence_ids': 'method_gap_matrix.csv',
        'evidence_locations': 'outputs/method_gap_matrix.csv (method_gap_merge.py output)',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: confirm tag columns after merge',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 MGA update (supersedes 67-paper basis in MGA-007; 87 papers tagged)'
    },
    {
        'claim_id': 'DT-004',
        'claim_text': 'Batch 6 is fully disposed: 15 of 20 papers finalized as include_core/include_supporting and 5 paywalled ranks (13, 23, 26, 32, 40) recorded as unresolved (FU1_FULLTEXT_UNAVAILABLE) with empty extraction_id after lawful acquisition attempts failed.',
        'scope': 'Full-text screening, batch 6',
        'evidence_ids': 'full_text_decisions.csv; FTA_20260731T121706Z/summary.csv',
        'evidence_locations': 'data/curated/screening/full_text_decisions.csv ranks 6,11,13,14,17,23,25,26,28,29,30,31,32,33,34,35,38,39,40,41; outputs/fulltext/acquisition/FTA_20260731T121706Z/summary.csv',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: confirm the 5 paywalled papers cannot be lawfully acquired',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-6 full-text completion'
    },
]


def read(path):
    return list(csv.DictReader(open(path, 'r', encoding='utf-8-sig')))


def write(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def update_registry():
    p = Path('outputs/dataset_registry.csv')
    rows = read(p)
    have = {(r['paper_id'], r['dataset_name']) for r in rows}
    added = 0
    for nr in NEW_REGISTRY:
        if (nr['paper_id'], nr['dataset_name']) in have:
            print(f'SKIP (exists): {nr["dataset_name"]}')
            continue
        rows.append(nr)
        have.add((nr['paper_id'], nr['dataset_name']))
        added += 1
        print(f'ADDED registry: {nr["dataset_name"]}')
    write(p, list(NEW_REGISTRY[0].keys()), rows)
    print(f'registry now {len(rows)} rows (+{added})')


def update_scores():
    p = Path('outputs/dataset_opportunity_scores.csv')
    rows = read(p)
    have = {(r['paper_id'], r['dataset_name']) for r in rows}
    added = 0
    for nr in NEW_SCORES:
        if (nr['paper_id'], nr['dataset_name']) in have:
            print(f'SKIP (exists): {nr["dataset_name"]}')
            continue
        rows.append(nr)
        have.add((nr['paper_id'], nr['dataset_name']))
        added += 1
        print(f'ADDED scores: {nr["dataset_name"]}')

    def key(r):
        return (-float(r['total']), r['dataset_name'])

    for r in rows:
        total = sum(float(r[k]) for k in
                    ('data_richness', 'underuse', 'novelty_fit',
                     'feasibility', 'publication_leverage'))
        r['total'] = f'{total:.1f}'
    rows.sort(key=key)
    for i, r in enumerate(rows, 1):
        r['rank'] = str(i)
    write(p, list(NEW_SCORES[0].keys()), rows)
    print(f'opportunity scores now {len(rows)} rows (+{added}), re-ranked 1..{len(rows)}')


def update_claims():
    p = Path('data/curated/claim_ledger.csv')
    rows = read(p)
    fieldnames = list(rows[0].keys()) if rows else list(NEW_CLAIMS[0].keys())
    have = {r['claim_id'] for r in rows}
    added = 0
    for nc in NEW_CLAIMS:
        if nc['claim_id'] in have:
            print(f'SKIP (exists): {nc["claim_id"]}')
            continue
        rows.append({k: nc.get(k, '') for k in fieldnames})
        have.add(nc['claim_id'])
        added += 1
        print(f'ADDED claim: {nc["claim_id"]}')
    write(p, fieldnames, rows)
    print(f'ledger now {len(rows)} rows (+{added})')


if __name__ == '__main__':
    update_registry()
    update_scores()
    update_claims()
    print('done')
