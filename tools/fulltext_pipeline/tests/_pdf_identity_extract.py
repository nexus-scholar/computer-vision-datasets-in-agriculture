from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

FILES = [
    r"C:\Users\mouadh\Downloads\1-s2.0-S0168169922000369-main.pdf",
    r"C:\Users\mouadh\Downloads\remotesensing-12-01246.pdf",
    r"C:\Users\mouadh\Downloads\cicba2017a.pdf",
    r"C:\Users\mouadh\Downloads\Estimating_the_LAI_IROS2017.pdf",
    r"C:\Users\mouadh\Downloads\Early_season_weed_mapping_in_sunflower_u.pdf",
    r"C:\Users\mouadh\Downloads\qt4s54k5n0_noSplash_5369fde315388269203db43f38fd4cc8.pdf",
    r"C:\Users\mouadh\Downloads\ESWAPrecAgric2015.pdf",
    r"C:\Users\mouadh\Downloads\Applepeachandpearflowerdetectionusingsemanticsegmentationnetworkandshapeconstraintlevelset.pdf",
    r"C:\Users\mouadh\Downloads\agriengineering-06-00119.pdf",
    r"C:\Users\mouadh\Downloads\Overview_of_the_radiometric_and_biophysi.pdf",
    r"C:\Users\mouadh\Downloads\Roth_et_al_2018_ISPRS.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2772375526002200-main.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S1574954124000888-main (1).pdf",
    r"C:\Users\mouadh\Downloads\Sensors_and_systems_for_fruit_detection.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2772375526001188-main.pdf",
    r"C:\Users\mouadh\Downloads\s41597-024-02945-6.pdf",
    r"C:\Users\mouadh\Downloads\remotesensing-16-04720-v2.pdf",
    r"C:\Users\mouadh\Downloads\Wang_Weed_Mapping_with_Convolutional_Neural_Networks_on_High_Resolution_Whole-Field_ICCVW_2023_paper.pdf",
    r"C:\Users\mouadh\Downloads\Advancements_in_Precision_Spraying_of_Agricultural_Robots_A_Comprehensive_Review.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S0168169919316266-am.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S0168169923001047-am.pdf",
    r"C:\Users\mouadh\Downloads\s41597-026-07074-w.pdf",
    r"C:\Users\mouadh\Downloads\plphys_v166_4_1688.pdf",
    r"C:\Users\mouadh\Downloads\SegFormer-Based_Cotton_Planting_Areas_Extraction_from_High-Resolution_Remote_Sensing_Images.pdf",
    r"C:\Users\mouadh\Downloads\2310.11516v2.pdf",
    r"C:\Users\mouadh\Downloads\chong2023ral.pdf",
    r"C:\Users\mouadh\Downloads\weyler2022wacv.pdf",
    r"C:\Users\mouadh\Downloads\remotesensing-12-03164-v2.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S1569843226002773-main.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2215016125000172-main.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S1110016826000499-main.pdf",
    r"C:\Users\mouadh\Downloads\sensors-17-02307.pdf",
    r"C:\Users\mouadh\Downloads\marks2022icra.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2772375524001436-main.pdf",
    r"C:\Users\mouadh\Downloads\ECPA23.pdf",
    r"C:\Users\mouadh\Downloads\Semiautonomous_Precision_Pruning_of_Upright_Fruiting_Offshoot_Orchard_Systems_An_Integrated_Approach.pdf",
    r"C:\Users\mouadh\Downloads\Wireless Communications and Mobile Computing - 2022 - Kamal - FCN Network‐Based Weed and Crop Segmentation for IoT‐Aided.pdf",
    r"C:\Users\mouadh\Downloads\agriculture-15-01723-v2.pdf",
    r"C:\Users\mouadh\Downloads\drones-07-00624-v2.pdf",
    r"C:\Users\mouadh\Downloads\Panoptic_Segmentation_With_Partial_Annotations_for_Agricultural_Robots.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2405896316316391-main.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S0168169919313237-main.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2214514121000829-main.pdf",
    r"C:\Users\mouadh\Downloads\make-08-00044-v2.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2589721724000266-main.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2589721724000205-main.pdf",
    r"C:\Users\mouadh\Downloads\jae-54-1-1432 (1).pdf",
    r"C:\Users\mouadh\Downloads\jae-54-1-1432.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S153751102300171X-main.pdf",
    r"C:\Users\mouadh\Downloads\remotesensing-12-02136-v2.pdf",
    r"C:\Users\mouadh\Downloads\Optical_flow-based_branch_segmentation_for_complex_orchard_environments.pdf",
    r"C:\Users\mouadh\Downloads\sensors-23-03670-v4.pdf",
    r"C:\Users\mouadh\Downloads\Investigation_on_Object_Detection_Models_for_Plant_Disease_Detection_Framework.pdf",
    r"C:\Users\mouadh\Downloads\agronomy-13-01846.pdf",
    r"C:\Users\mouadh\Downloads\High_Precision_Leaf_Instance_Segmentation_for_Phenotyping_in_Point_Clouds_Obtained_Under_Real_Field_Conditions.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2590005625000396-main.pdf",
    r"C:\Users\mouadh\Downloads\agronomy-14-01178-v2.pdf",
    r"C:\Users\mouadh\Downloads\remotesensing-10-00285.pdf",
    r"C:\Users\mouadh\Downloads\Semantic_Segmentation_of_Crops_and_Weeds_with_Probabilistic_Modeling_and_Uncertainty_Quantification.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S0303243420309259-main.pdf",
    r"C:\Users\mouadh\Downloads\Wireless_Collaborative_Inference_Acceleration_Based_on_Distillation_for_Weed_Detection_and_Instance_Segmentation.pdf",
    r"C:\Users\mouadh\Downloads\s41597-026-06926-9_reference.pdf",
    r"C:\Users\mouadh\Downloads\s00530-023-01158-y.pdf",
    r"C:\Users\mouadh\Downloads\Zero-Shot_Semantic_Segmentation_for_Robots_in_Agriculture.pdf",
    r"C:\Users\mouadh\Downloads\s41597-025-06513-4.pdf",
    r"C:\Users\mouadh\Downloads\s41597-026-07092-8.pdf",
    r"C:\Users\mouadh\Downloads\s41597-025-06049-7.pdf",
    r"C:\Users\mouadh\Downloads\agronomy-13-01503-v2.pdf",
    r"C:\Users\mouadh\Downloads\remotesensing-10-01690.pdf",
    r"C:\Users\mouadh\Downloads\FieldPlant_A_Dataset_of_Field_Plant_Images_for_Plant_Disease_Detection_and_Classification_With_Deep_Learning.pdf",
    r"C:\Users\mouadh\Downloads\Towards_Accurate_Disease_Segmentation_in_Plant_Images_A_Comprehensive_Dataset_Creation_and_Network_Evaluation.pdf",
    r"C:\Users\mouadh\Downloads\PLANesT-3D_A_New_Annotated_Data_Set_of_3D_Color_Point_Clouds_of_Plants.pdf",
    r"C:\Users\mouadh\Downloads\2403.00566v1.pdf",
    r"C:\Users\mouadh\Downloads\j.smartag.SA202410032.pdf",
    r"C:\Users\mouadh\Downloads\2312.14706v2.pdf",
    r"C:\Users\mouadh\Downloads\1-s2.0-S2643651525001141-main.pdf",
]

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"']+", re.IGNORECASE)
ARXIV_RE = re.compile(r"\b(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def first_page_text(doc: fitz.Document, page_idx: int = 0) -> str:
    page = doc[page_idx]
    blocks = page.get_text("blocks")
    blocks.sort(key=lambda b: (b[1], b[0]))
    lines = [clean(b[4]) for b in blocks if b[4].strip()]
    return "\n".join(lines)

out = []
for path_str in FILES:
    path = Path(path_str)
    rec = {"file": path.name, "path": str(path), "ok": False}
    try:
        with path.open("rb") as fh:
            data = fh.read()
        rec["sha256"] = hashlib.sha256(data).hexdigest()
        rec["size_bytes"] = len(data)
        doc = fitz.open(path)
        rec["pages"] = doc.page_count
        meta = doc.metadata or {}
        rec["meta_title"] = clean(meta.get("title", ""))
        rec["meta_author"] = clean(meta.get("author", ""))
        first = first_page_text(doc, 0)
        rec["first_text"] = first[:3000]
        dois = DOI_RE.findall(first)
        rec["dois_first"] = [d.rstrip(").,;]") for d in dois]
        if not rec["dois_first"] and rec["meta_title"]:
            rec["dois_first"] = DOI_RE.findall(rec["meta_title"])
        arx = ARXIV_RE.findall(first)
        rec["arxiv_first"] = arx
        if not rec["arxiv_first"] and rec["meta_title"]:
            rec["arxiv_first"] = ARXIV_RE.findall(rec["meta_title"])
        rec["ok"] = True
        doc.close()
    except Exception as exc:
        rec["error"] = str(exc)
    out.append(rec)

out_path = Path(__file__).resolve().parents[3] / "outputs" / "manual_pdf_identities_20260803.json"
out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out_path}")
print(f"ok: {sum(1 for r in out if r['ok'])} / {len(out)}")
for r in out:
    if not r["ok"]:
        print("FAILED:", r["file"], r.get("error"))
