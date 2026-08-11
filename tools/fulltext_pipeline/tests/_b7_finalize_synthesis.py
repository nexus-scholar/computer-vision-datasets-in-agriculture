"""Finalize batch-7 evidence synthesis.

Appends 5 newly introduced datasets to the dataset registry, re-ranks
opportunity scores deterministically, and appends claim-ledger entries.

Idempotent: skips rows whose (paper_id, dataset_name) or claim_id already exist.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, 'tools/fulltext_pipeline/src')

REVIEWED_AT = '2026-08-03'

NEW_REGISTRY = [
    {
        'paper_id': 'doi:10.1186/s13007-025-01334-3',
        'dataset_name': 'Seedling RGB-depth dataset (DATA INRAE)',
        'crop': 'rapeseed, tomato, bean',
        'task': 'pot-scale growth-stage classification, seedling detection/segmentation',
        'modality': 'RGB-D (RGB + aligned depth, time-lapse)',
        'platform': '8x Intel RealSense D435 (ground-based, 15-min frame rate)',
        'image_count': '6,040 pot time-lapses; 1,216 labelled; 69,946 RGB-depth full frames; >700k plant annotations',
        'license': 'not specified (DATA INRAE repository, doi:10.57745/AMFJTK)',
        'access_url': 'https://doi.org/10.57745/AMFJTK',
        'annotation_type': 'per-pot growth-stage labels (soil, cotyledon appearance, cotyledon opening, first leaf); plant annotations',
        'notes': 'Data paper; 11 trials in 2022 across 3 crops; 1920x1080 RGB + aligned 1280x720 depth; 80/10/10 pot-time-lapse-level split; CNN baseline 88.7% overall accuracy.',
    },
    {
        'paper_id': 'doi:10.34133/plantphenomics.0080',
        'dataset_name': 'Soybean MVSP2 spatiotemporal point-cloud dataset',
        'crop': 'soybean',
        'task': 'point-wise semantic segmentation (stem/leaf), leaf-instance segmentation',
        'modality': '3D point cloud (photogrammetry from multi-view RGB)',
        'platform': 'MVSP2 rig (Panasonic LUMIX DMC-G7W + Agisoft Metashape)',
        'image_count': '258 point clouds from 30 plants; 145 point-wise annotated',
        'license': 'not specified (available on request)',
        'access_url': 'not specified (available on request)',
        'annotation_type': 'point-level stem/leaf semantic labels with unique leaf-instance IDs',
        'notes': 'Acquired May 6-27 2022; weakly supervised Eff-3DPSeg (soybean stem-leaf F1 95.8%, mIoU 92.2% at 200 labeled points); also evaluates on Pheno4D tomato subset; code github.com/jieyi-one/EFF-3DPSEG.',
    },
    {
        'paper_id': 'doi:10.1016/j.compag.2022.107091',
        'dataset_name': 'CottonWeedID15',
        'crop': 'cotton (15 weed classes, southern US)',
        'task': 'multiclass weed classification',
        'modality': 'RGB',
        'platform': 'field collection 2020-2021 seasons (camera unspecified)',
        'image_count': '5,187 images',
        'license': 'not specified (public on Kaggle)',
        'access_url': 'Kaggle (URL in paper Section 2.1 footnote)',
        'annotation_type': 'image-level class labels (15 weed classes)',
        'notes': 'Collected primarily in Mississippi and North Carolina; 65/20/15 train/val/test split; 27 ImageNet-pretrained CNNs benchmarked; ResNet101 test F1 99.1%; weighted cross-entropy improves minority classes; DeepWeeds/Plant Seedlings/Early Crop Weeds cited only.',
    },
    {
        'paper_id': 'doi:10.1109/iros47612.2022.9981304',
        'dataset_name': 'CN20',
        'crop': 'corn (9 weed categories)',
        'task': 'instance segmentation, bounding-box detection, stem localization, field monitoring',
        'modality': 'RGB-D (RGB + depth)',
        'platform': 'BonnBot-I field robot (Intel RealSense D435i, nadir view)',
        'image_count': '283 RGB-D frames (170 train / 43 val / 70 test); 2,566 crop + 1,261 weed instances',
        'license': 'not specified (author claims public availability)',
        'access_url': 'not specified (no URL or DOI in paper text)',
        'annotation_type': 'instance segmentation masks, bounding boxes, stem locations (COCO format)',
        'notes': 'Six rows at Campus Klein-Altendorf (CKA), University of Bonn; field-monitoring NAE improved 8.3% to 3.5%; weeding-planning experiments also use the SB20 sugar-beet dataset (Halstead et al. 2021).',
    },
    {
        'paper_id': 'doi:10.3389/fpls.2020.00751',
        'dataset_name': 'GLDD (Grape Leaf Disease Dataset)',
        'crop': 'grape (4 diseases: Black rot, Black measles/Esca, Leaf blight, Mites of grape)',
        'task': 'real-time disease detection (object detection)',
        'modality': 'RGB',
        'platform': 'laboratory + Wei Jiani Chateau vineyard (Yinchuan, Ningxia, China)',
        'image_count': '4,449 original images; augmented 14x to 62,286',
        'license': 'not specified (available on request)',
        'access_url': 'not specified (on request to corresponding author)',
        'annotation_type': 'expert-annotated rectangular bounding boxes (4 disease classes)',
        'notes': '3:1:1 train/val/test split (37,371/12,457/12,458); Faster DR-IACNN detector 81.1% mAP at 15.01 FPS.',
    },
]

NEW_SCORES = [
    {
        'paper_id': 'doi:10.1186/s13007-025-01334-3',
        'dataset_name': 'Seedling RGB-depth dataset (DATA INRAE)',
        'modality': 'RGB-D (time-lapse)',
        'task': 'pot-scale growth-stage classification, seedling detection/segmentation',
        'data_richness': '4.0',
        'underuse': '4.5',
        'novelty_fit': '4.0',
        'feasibility': '4.5',
        'publication_leverage': '3.5',
        'notes': 'Public RGB-depth time-lapse, 3 crops, 11 trials, >700k plant annotations, pot-level split; depth + temporal structure enable sensor-conditioning and domain-shift experiments.',
    },
    {
        'paper_id': 'doi:10.34133/plantphenomics.0080',
        'dataset_name': 'Soybean MVSP2 spatiotemporal point-cloud dataset',
        'modality': '3D point cloud (photogrammetry)',
        'task': 'point-wise semantic segmentation, leaf-instance segmentation',
        'data_richness': '3.5',
        'underuse': '4.5',
        'novelty_fit': '4.5',
        'feasibility': '2.5',
        'publication_leverage': '4.0',
        'notes': 'Temporal 3D organ-level segmentation with weakly-supervised labels; request-only data lowers feasibility despite public code.',
    },
    {
        'paper_id': 'doi:10.1109/iros47612.2022.9981304',
        'dataset_name': 'CN20',
        'modality': 'RGB-D',
        'task': 'instance segmentation, detection, stem localization, field monitoring',
        'data_richness': '3.5',
        'underuse': '4.5',
        'novelty_fit': '4.0',
        'feasibility': '2.5',
        'publication_leverage': '3.5',
        'notes': 'RGB-D crop/weed with instance masks + stem locations; public-availability claim is unverifiable (no URL/DOI in text).',
    },
    {
        'paper_id': 'doi:10.1016/j.compag.2022.107091',
        'dataset_name': 'CottonWeedID15',
        'modality': 'RGB',
        'task': 'multiclass weed classification',
        'data_richness': '3.0',
        'underuse': '3.5',
        'novelty_fit': '2.5',
        'feasibility': '4.5',
        'publication_leverage': '2.5',
        'notes': 'Public Kaggle RGB classification dataset (15 classes, 2 seasons); no stated license is a reuse-pathway risk.',
    },
    {
        'paper_id': 'doi:10.3389/fpls.2020.00751',
        'dataset_name': 'GLDD (Grape Leaf Disease Dataset)',
        'modality': 'RGB',
        'task': 'real-time disease detection',
        'data_richness': '2.5',
        'underuse': '3.5',
        'novelty_fit': '2.5',
        'feasibility': '2.0',
        'publication_leverage': '2.5',
        'notes': 'Request-only grape disease detection with expert bboxes; standard task and limited public access.',
    },
]

NEW_CLAIMS = [
    {
        'claim_id': 'DSO-011',
        'claim_text': 'The Seedling RGB-depth dataset (rank 139) is the top-ranked newly introduced batch-7 dataset (20.5/25): a public RGB-depth time-lapse of seedling development across 3 crops with >700k plant annotations and a pot-level 80/10/10 split, enabling depth-modality and temporal-domain-shift experiments.',
        'scope': 'Seedling RGB-depth dataset (rank 139)',
        'evidence_ids': 'doi:10.1186/s13007-025-01334-3',
        'evidence_locations': 'FTS_14de9157d8409d0cdb96; full_text_decisions.csv rank 139; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm DATA INRAE dataset license and download terms; reconcile >700k plant annotations vs 1,216 labelled time-lapses',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-7 evidence synthesis'
    },
    {
        'claim_id': 'DSO-012',
        'claim_text': 'The Soybean MVSP2 spatiotemporal point-cloud dataset (rank 149) is the top-ranked newly introduced batch-7 3D dataset (19.0/25): temporal 3D point clouds with point-wise stem/leaf and leaf-instance labels and a public code repository, limited by request-only data access (feasibility 2.5/5).',
        'scope': 'Soybean MVSP2 point-cloud dataset (rank 149)',
        'evidence_ids': 'doi:10.34133/plantphenomics.0080',
        'evidence_locations': 'FTS_8e1e29cab85894959122; full_text_decisions.csv rank 149; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'moderate',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm request-only availability and license terms',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-7 evidence synthesis'
    },
    {
        'claim_id': 'DSO-013',
        'claim_text': 'CN20 (rank 212) is a corn RGB-D crop/weed dataset with instance masks, bounding boxes, and stem locations in COCO format, but its public-availability claim is unverifiable because the paper provides no URL or DOI, limiting feasibility (2.5/5).',
        'scope': 'CN20 dataset (rank 212)',
        'evidence_ids': 'doi:10.1109/iros47612.2022.9981304',
        'evidence_locations': 'FTS_86107136ed60e764d9c2; full_text_decisions.csv rank 212; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'weak',
        'uncertainty': 'high',
        'status': 'proposed',
        'required_validation': 'human: locate CN20 repository or confirm access terms',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-7 evidence synthesis'
    },
    {
        'claim_id': 'DSO-014',
        'claim_text': 'CottonWeedID15 (rank 150) is a public Kaggle RGB weed-classification dataset (5,187 images, 15 classes, two seasons) with high feasibility (4.5/5) but no stated license, a reuse-pathway risk for downstream publication.',
        'scope': 'CottonWeedID15 dataset (rank 150)',
        'evidence_ids': 'doi:10.1016/j.compag.2022.107091',
        'evidence_locations': 'FTS_9ad93565f1aac789c53b; full_text_decisions.csv rank 150; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'weak',
        'uncertainty': 'high',
        'status': 'proposed',
        'required_validation': 'human: verify Kaggle license/terms for CottonWeedID15',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-7 evidence synthesis'
    },
    {
        'claim_id': 'DSO-015',
        'claim_text': 'GLDD (rank 334) is a request-only grape leaf disease detection dataset (4,449 original images augmented 14x to 62,286, expert bounding boxes) whose request-only access and standard RGB detection task limit its opportunity (13.0/25).',
        'scope': 'GLDD (Grape Leaf Disease Dataset), rank 334',
        'evidence_ids': 'doi:10.3389/fpls.2020.00751',
        'evidence_locations': 'FTS_8f7b35f7cdb6938fce72; full_text_decisions.csv rank 334; outputs/dataset_registry.csv; outputs/dataset_opportunity_scores.csv',
        'contradictory_evidence': '',
        'strength': 'weak',
        'uncertainty': 'medium',
        'status': 'proposed',
        'required_validation': 'human: confirm request-only availability',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-7 evidence synthesis'
    },
    {
        'claim_id': 'DT-005',
        'claim_text': 'Batch 7 is fully disposed: 7 of 20 ranks finalized as include_core/include_supporting (ranks 139, 149, 150, 155, 212, 268, 334) and 13 ranks recorded unresolved (FU1_FULLTEXT_UNAVAILABLE, empty extraction_id) after lawful acquisition failed (403 Forbidden, no_candidate, or XML-only coredata stub).',
        'scope': 'Full-text screening, batch 7',
        'evidence_ids': 'full_text_decisions.csv; FTA_20260803T005806Z/summary.csv',
        'evidence_locations': 'data/curated/screening/full_text_decisions.csv ranks 52,62,78,103,105,106,109,114,117,139,145,149,150,155,184,188,212,268,278,334; outputs/fulltext/acquisition/FTA_20260803T005806Z/summary.csv',
        'contradictory_evidence': '',
        'strength': 'strong',
        'uncertainty': 'low',
        'status': 'proposed',
        'required_validation': 'human: confirm the 13 paywalled papers cannot be lawfully acquired, or accept user-supplied PDFs for later import',
        'reviewer': 'opencode_ai',
        'reviewed_at': REVIEWED_AT,
        'notes': 'Batch-7 full-text completion'
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
    fieldnames = list(rows[0].keys())
    have = {(r['paper_id'], r['dataset_name']) for r in rows}
    added = 0
    for nr in NEW_REGISTRY:
        if (nr['paper_id'], nr['dataset_name']) in have:
            print(f'SKIP (exists): {nr["dataset_name"]}')
            continue
        rows.append({k: nr.get(k, '') for k in fieldnames})
        have.add((nr['paper_id'], nr['dataset_name']))
        added += 1
        print(f'ADDED registry: {nr["dataset_name"]}')
    write(p, fieldnames, rows)
    print(f'registry now {len(rows)} rows (+{added})')


def update_scores():
    p = Path('outputs/dataset_opportunity_scores.csv')
    rows = read(p)
    fieldnames = list(rows[0].keys())
    have = {(r['paper_id'], r['dataset_name']) for r in rows}
    added = 0
    for nr in NEW_SCORES:
        if (nr['paper_id'], nr['dataset_name']) in have:
            print(f'SKIP (exists): {nr["dataset_name"]}')
            continue
        rows.append({k: nr.get(k, '') for k in fieldnames})
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
    write(p, fieldnames, rows)
    print(f'opportunity scores now {len(rows)} rows (+{added}), re-ranked 1..{len(rows)}')


def update_claims():
    p = Path('data/curated/claim_ledger.csv')
    rows = read(p)
    fieldnames = list(rows[0].keys())
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
