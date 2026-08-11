"""Deterministic correction event: apply human-audited dataset-registry
license/access corrections (2026-08-11).

Each correction is keyed by paper_id and asserts the exact current cell value
before overwriting, so an unexpected drift aborts instead of corrupting rows.
Audit provenance is appended to each row's notes (audit id + date).

Corrections (all from human-verified audits recorded in data/curated/audit_log.csv):
  2. WeedElec            doi:10.1002/aps3.11373        license not specified -> cc-by-4.0            (audit DT-003, AUDIT_20260811185337353209)
  3. ROSE-X              doi:10.1186/s13007-020-00573-w license cell is article license; data CC0    (audit DT-003, AUDIT_20260811185337353209)
  4. Two-Season-WeedDet8 doi:10.1016/j.ecoinf.2024.102546 CC-BY-NC-ND-4.0 -> CC-BY-NC-4.0            (audit DSO-007, AUDIT_20260811190243951807)
  5. AgriAdapt           doi:10.3390/electronics14204082 image_count + note: repo confirms 643       (audit DSO-008, AUDIT_20260811191013616048)
  6. 3D Rice WBPH Damage doi:10.3390/agriculture16020215 license: article vs data (request-only)      (audit DSO-009, AUDIT_20260811191547313448)
  7. Bean Soy UAV        doi:10.3390/rs16234394        access_url public Roboflow (CC BY 4.0)        (audit DSO-010, AUDIT_20260811192706592053)
  8. Seedling RGB-depth  doi:10.1186/s13007-025-01334-3 license not specified -> etalab-2.0 + notes  (audit DSO-011, AUDIT_20260811202532328655)
  9. CN20                doi:10.1109/iros47612.2022.9981304 access_url + notes (located, stale link)  (audit DSO-013, AUDIT_20260811204242277184)
 10. CottonWeedID15      doi:10.1016/j.compag.2022.107091  license not specified -> CC-BY-NC-4.0     (audit DSO-014, AUDIT_20260811204641765685)
 11. MaizeField3D        doi:10.31274/td-20260223-107       license not specified -> CC-BY-NC-4.0     (audit DSO-016, AUDIT_20260811214930407636)
 12. OPPD                doi:10.3390/rs12081246             license not specified -> CC-BY-NC-SA-4.0   (audit DSO-017, AUDIT_20260811215433379299)
 13. BonnBeetClouds3D    doi:10.1109/iros58592.2024.10802820 license not specified -> CC0-1.0           (audit DSO-018, AUDIT_20260811215745685855)

This script never touches claim_ledger.csv or full_text_decisions.csv.
"""

from pathlib import Path
from typing import Any

from agri_fulltext.io_utils import atomic_write_csv, now_utc, read_csv

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "outputs" / "dataset_registry.csv"

# (paper_id, field, expected_value, new_value)
CORRECTIONS: list[tuple[str, str, str, str]] = [
    (
        "doi:10.1002/aps3.11373",
        "license",
        "not specified",
        "cc-by-4.0",
    ),
    (
        "doi:10.1002/aps3.11373",
        "notes",
        "2489 manually annotated plant instances across 7 categories; Mask R-CNN (ResNet-50+FPN) baseline; mean AP=0.49; Zenodo open access.",
        "2489 manually annotated plant instances across 7 categories; Mask R-CNN (ResNet-50+FPN) baseline; mean AP=0.49; Zenodo open access. [Correction 2026-08-11, audit AUDIT_20260811185337353209]: license confirmed cc-by-4.0 via Zenodo API license.id.",
    ),
    (
        "doi:10.1186/s13007-020-00573-w",
        "notes",
        "Available in volumetric and point-cloud forms; baseline methods include 3D U-Net, LFVD (RF), LFPC; best leaf IoU 97.93%, stem IoU 86.23%.",
        "Available in volumetric and point-cloud forms; baseline methods include 3D U-Net, LFVD (RF), LFPC; best leaf IoU 97.93%, stem IoU 86.23%. [Correction 2026-08-11, audit AUDIT_20260811185337353209]: license cell reflects the ARTICLE license (CC BY 4.0); the DATASET itself falls under the BMC default CC0 waiver (uabox.univ-angers.fr ownCloud archive, no data credit line found).",
    ),
    (
        "doi:10.1016/j.ecoinf.2024.102546",
        "license",
        "CC-BY-NC-ND-4.0",
        "CC-BY-NC-4.0",
    ),
    (
        "doi:10.1016/j.ecoinf.2024.102546",
        "notes",
        "Two seasons 2021+2022; 2021 subset from CottonWeedDet12; GitHub CrossSeasonWeedDetection; cross-season detection benchmark.",
        "Two seasons 2021+2022; 2021 subset from CottonWeedDet12; GitHub CrossSeasonWeedDetection; cross-season detection benchmark. [Correction 2026-08-11, audit AUDIT_20260811190243951807]: Zenodo record 10762138 rev10 + DataCite SPDX cc-by-nc-4.0; no ND term (derivatives permitted with attribution; NC blocks commercial use).",
    ),
    (
        "doi:10.3390/electronics14204082",
        "image_count",
        "643 (text) / 747 (abstract) high-resolution aerial images (discrepancy); 1280x1280, GSD 0.4 cm/px; 322 Field_ID_1 + 321 Field_ID_2",
        "643 high-resolution aerial images (322 Field_ID_1 + 321 Field_ID_2); 1280x1280, GSD 0.4 cm/px; Roboflow Universe confirms 643 (visited 2026-08-11); 747 appears only in intro/contributions (stale).",
    ),
    (
        "doi:10.3390/electronics14204082",
        "notes",
        "Two fields in Rome, Italy; on-board real-time detection; text vs abstract image-count inconsistency (643 vs 747) flagged.",
        "Two fields in Rome, Italy; on-board real-time detection. [Correction 2026-08-11, audit AUDIT_20260811191013616048]: inconsistency resolved - abstract + S3 state 643 (322+321), intro/contributions state 747 (stale); live Roboflow Universe page confirms 643 images.",
    ),
    (
        "doi:10.3390/agriculture16020215",
        "license",
        "CC-BY-4.0",
        "CC-BY-4.0 (article); data = request-only, no stated license terms",
    ),
    (
        "doi:10.3390/agriculture16020215",
        "notes",
        "Test set = final collection of each pot (grouped split by pot); baselines PointNet/PointNet++/ShellNet/PointCNN; Data Availability on request.",
        "Test set = final collection of each pot (grouped split by pot); baselines PointNet/PointNet++/ShellNet/PointCNN; Data Availability on request. [Correction 2026-08-11, audit AUDIT_20260811191547313448]: data available only on request with no stated license terms; article license CC-BY-4.0 does not extend to the data.",
    ),
    (
        "doi:10.1186/s13007-025-01334-3",
        "license",
        "not specified (DATA INRAE repository, doi:10.57745/AMFJTK)",
        "etalab-2.0 (open, CC-BY-2.0-compatible; DATA INRAE repository doi:10.57745/AMFJTK, public per-file download)",
    ),
    (
        "doi:10.1186/s13007-025-01334-3",
        "notes",
        "Data paper; 11 trials in 2022 across 3 crops; 1920x1080 RGB + aligned 1280x720 depth; 80/10/10 pot-time-lapse-level split; CNN baseline 88.7% overall accuracy.",
        "Data paper; 11 trials in 2022 across 3 crops; 1920x1080 RGB + aligned 1280x720 depth; 80/10/10 pot-time-lapse-level split; CNN baseline 88.7% overall accuracy. [Correction 2026-08-11, audit AUDIT_20260811202532328655]: license verified Etalab Open License 2.0 (SPDX etalab-2.0, CC-BY-2.0 compatible); public per-file download (15 files, ID-01..ID-10 trial zips 5.7-34.0 GB + xlsx/readme), no login; 1,216 labelled pot time-lapses = sequences (Table 2: 336+480+400), >700k = annotated pot frames (Table 4 split 972+122+122 = 762,106 frames with per-pot growth-stage labels); no contradiction.",
    ),
    (
        "doi:10.1109/iros47612.2022.9981304",
        "access_url",
        "not specified (no URL or DOI in paper text)",
        "AgRobotics page https://agrobotics.uni-bonn.de/corn_2020_dataset/index.html (live 2026-08-11) -> sciebo share https://uni-bonn.sciebo.de/s/HpUV7A1KofVop9u (404 as of 2026-08-11; functional per Wayback 2024-04-20, CN20.tar.gz 23.5 GB); PhenoRoam metadata-only record 10f2b8b0-bb8a-4b1c-864c-060a5462dcb7",
    ),
    (
        "doi:10.1109/iros47612.2022.9981304",
        "notes",
        "Six rows at Campus Klein-Altendorf (CKA), University of Bonn; field-monitoring NAE improved 8.3% to 3.5%; weeding-planning experiments also use the SB20 sugar-beet dataset (Halstead et al. 2021).",
        "Six rows at Campus Klein-Altendorf (CKA), University of Bonn; field-monitoring NAE improved 8.3% to 3.5%; weeding-planning experiments also use the SB20 sugar-beet dataset (Halstead et al. 2021). [Correction 2026-08-11, audit AUDIT_20260811204242277184]: public availability verified via AgRobotics project page; primary sciebo download link stale (404 2026-08-11, was functional 2024-04-20 per Wayback; CN20.tar.gz 23.5 GB); PhenoRoam record is metadata-only; no license terms stated anywhere. Feasibility 2.5/5 retained with corrected rationale (stale link + no license), not 'unverifiable'.",
    ),
    (
        "doi:10.1016/j.compag.2022.107091",
        "license",
        "not specified (public on Kaggle)",
        "CC-BY-NC-4.0 (Kaggle API record 2026-08-11; non-commercial use only)",
    ),
    (
        "doi:10.1016/j.compag.2022.107091",
        "notes",
        "Collected primarily in Mississippi and North Carolina; 65/20/15 train/val/test split; 27 ImageNet-pretrained CNNs benchmarked; ResNet101 test F1 99.1%; weighted cross-entropy improves minority classes; DeepWeeds/Plant Seedlings/Early Crop Weeds cited only.",
        "Collected primarily in Mississippi and North Carolina; 65/20/15 train/val/test split; 27 ImageNet-pretrained CNNs benchmarked; ResNet101 test F1 99.1%; weighted cross-entropy improves minority classes; DeepWeeds/Plant Seedlings/Early Crop Weeds cited only. [Correction 2026-08-11, audit AUDIT_20260811204641765685]: license verified via Kaggle API record yuzhenlu/cottonweedid15 = CC BY-NC 4.0 (Attribution-NonCommercial, non-commercial use only); public, ~11.35 GB, v1. Paper text itself states no license; reuse restricted to non-commercial.",
    ),
    (
        "doi:10.31274/td-20260223-107",
        "license",
        "not specified",
        "CC-BY-NC-4.0 (Hugging Face BGLab/MaizeField3D record, verified 2026-08-11; non-commercial use only)",
    ),
    (
        "doi:10.31274/td-20260223-107",
        "notes",
        "Includes metadata and subsampled versions (100k/50k/10k points) with STL/DAT procedural outputs and code. A HELIOS canopy PAR simulation built from the procedural models validated simulated fPAR against field measurements (Pearson r=0.83, MAE=0.058).",
        "Includes metadata and subsampled versions (100k/50k/10k points) with STL/DAT procedural outputs and code. A HELIOS canopy PAR simulation built from the procedural models validated simulated fPAR against field measurements (Pearson r=0.83, MAE=0.058). [Correction 2026-08-11, audit AUDIT_20260811214930407636]: license verified CC-BY-NC-4.0 on Hugging Face record BGLab/MaizeField3D (public, non-commercial use only; 4.21 GB, 226 downloads last month). No published learning baseline confirmed - pure dataset article. Note: HF card title reads 'AgriField3D' (arXiv 2503.07813); registry DOI is the institutional DataShare record.",
    ),
    (
        "doi:10.3390/rs12081246",
        "license",
        "not specified",
        "CC-BY-NC-SA-4.0 (project page badge, verified 2026-08-11; non-commercial, share-alike)",
    ),
    (
        "doi:10.3390/rs12081246",
        "access_url",
        "https://vision.eng.au.dk/open-plant-phenotyping-database/",
        "https://vision.eng.au.dk/open-plant-phenotyping-database/ (download: https://gitlab.au.dk/AUENG-Vision/OPPD)",
    ),
    (
        "doi:10.3390/rs12081246",
        "notes",
        "315,038 bounding-box-annotated plant objects representing 64,292 temporally tracked individual plants cultivated under three growth conditions (G1 ideal, G2 drought, G3 natural) at the Aarhus University semifield, Research Centre Flakkebjerg, Denmark. 10-fold CV baselines: Faster R-CNN/ResNet50 plant detection AP 37.01 +/- 2.43; ResNet50 species classification accuracy 77.06 +/- 5.71.",
        "315,038 bounding-box-annotated plant objects representing 64,292 temporally tracked individual plants cultivated under three growth conditions (G1 ideal, G2 drought, G3 natural) at the Aarhus University semifield, Research Centre Flakkebjerg, Denmark. 10-fold CV baselines: Faster R-CNN/ResNet50 plant detection AP 37.01 +/- 2.43; ResNet50 species classification accuracy 77.06 +/- 5.71. [Correction 2026-08-11, audit AUDIT_20260811215433379299]: license verified CC-BY-NC-SA-4.0 (project page badge; non-commercial + share-alike - most restrictive of the top-5 candidate licenses). Public download at gitlab.au.dk/AUENG-Vision/OPPD. Note: majority of the 64,292 plants tracked only a few days due to continuous thinning (line 220), relevant if temporal re-identification is a planned use.",
    ),
    (
        "doi:10.1109/iros58592.2024.10802820",
        "license",
        "not specified",
        "CC0-1.0 (bonndata License/Data Use Agreement badge, verified 2026-08-11; public domain, most permissive of the top-5 candidate licenses)",
    ),
    (
        "doi:10.1109/iros58592.2024.10802820",
        "access_url",
        "bonnbeetclouds3d.ipb.uni-bonn.de",
        "https://bonnbeetclouds3d.ipb.uni-bonn.de (download: https://doi.org/10.60507/FK2/34W30T; Codabench challenge 4470)",
    ),
    (
        "doi:10.1109/iros58592.2024.10802820",
        "notes",
        "Reusable agricultural dataset of UAV photogrammetric point clouds of real sugar beet breeding trials (48 varieties, >3,000 plants). Includes 186 annotated plants, 2,661 leaf instances, >10,000 keypoints, expert phenotypic-trait reference measurements, a train/val/test split (1,782/260/619 leaves), and PLY patches. Publicly released with an associated challenge; baseline experiments in Tabs. III-V p. 7.",
        "Reusable agricultural dataset of UAV photogrammetric point clouds of real sugar beet breeding trials (48 varieties, >3,000 plants). Includes 186 annotated plants, 2,661 leaf instances, >10,000 keypoints, expert phenotypic-trait reference measurements, a train/val/test split (1,782/260/619 leaves), and PLY patches. Publicly released with an associated challenge; baseline experiments in Tabs. III-V p. 7. [Correction 2026-08-11, audit AUDIT_20260811215745685855]: license verified CC0-1.0 on bonndata (public domain, most permissive of the top-5 candidate licenses). Test-set labels appear withheld (line 94: labels provided for train and validation sets only); challenge-style evaluation via Codabench.",
    ),
    (
        "doi:10.3390/rs16234394",
        "access_url",
        "not specified (available on request)",
        "https://universe.roboflow.com/wwwdataset-jzoak/weed11-12dez22-6fev23-20m-2 (public download, CC BY 4.0)",
    ),
    (
        "doi:10.3390/rs16234394",
        "notes",
        "Acquired Dec 2022-Feb 2023 at Goiano Federal Institute-Campus Ceres, Brazil; random split; 8.92 avg weeds/picture; Data Availability on request despite abstract implying public access.",
        "Acquired Dec 2022-Feb 2023 at Goiano Federal Institute-Campus Ceres, Brazil; random split; 8.92 avg weeds/picture. [Correction 2026-08-11, audit AUDIT_20260811192706592053]: public release verified on Roboflow Universe (project weed11-12dez22-6fev23-20m-2, version /19 = 3,021 images, exactly the paper's augmented count; classes Weed/Bean/Soybean; CC BY 4.0). Paper Data Availability statement says 'on request' but the release is public; abstract is therefore correct. Feasibility score (2.5/5) understated - should be revisited upward pending human confirmation of re-scoring.",
    ),
]


def main() -> None:
    _, rows = read_csv(REGISTRY)
    by_paper: dict[str, dict[str, Any]] = {r.get("paper_id", ""): r for r in rows}
    stamp = now_utc()

    applied: list[str] = []
    skipped: list[str] = []
    for paper_id, field, expected, new_value in CORRECTIONS:
        row = by_paper.get(paper_id)
        if row is None:
            raise SystemExit(f"ABORT: {paper_id} not found in registry.")
        current = row.get(field, "")
        if current.strip() == new_value.strip():
            skipped.append(f"{paper_id} :: {field} (already applied)")
            continue
        if current.strip() != expected.strip():
            raise SystemExit(
                f"ABORT: {paper_id} field '{field}' drifted.\n  expected: {expected!r}\n  found:    {current!r}"
            )
        row[field] = new_value
        applied.append(f"{paper_id} :: {field}")

    if applied:
        fieldnames = list(rows[0].keys()) if rows else list(by_paper.values())[0].keys()
        atomic_write_csv(REGISTRY, fieldnames, rows)
    print(f"registry corrections applied ({stamp}):")
    for a in applied:
        print(f"  {a}")
    for s in skipped:
        print(f"  {s}")
    print(f"total rows: {len(rows)}")


if __name__ == "__main__":
    main()
