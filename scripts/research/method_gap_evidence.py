#!/usr/bin/env python3
"""Phase 2a: extract evidence snippets for each method dimension from paper.md.
Outputs outputs/method_gap_evidence.csv for LLM-based tagging."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools/fulltext_pipeline" / "src"))
from agri_fulltext.io_utils import read_csv, atomic_write_csv


DIMENSION_PATTERNS = {
    "split_level": [
        r"(?i)(random\s+split|train.?test\s+split|hold.?out)",
        r"(?i)(grouped\s+(split|cross.?val)|field.?level|plant.?level|time.?series\s+split|temporal\s+split)",
        r"(?i)(leave.?one\s+(field|plant|plot|out|time))",
        r"(?i)(stratified\s+split|cross.?validation)",
    ],
    "baseline_strength": [
        r"(?i)(support\s+vector|random\s+forest|logistic\s+regression|linear\s+regression|SVM|k.?NN|naive\s+bayes|decision\s+tree)",
        r"(?i)(baseline|benchmark|compared\s+with|state.?of.?the.?art|SOTA)",
        r"(?i)(outperform|improve\s+over|better\s+than)",
    ],
    "calibration_reported": [
        r"(?i)(calibration|uncertainty|confidence|reliability\s+diagram|ECE|expected\s+calibration|Brier|temperature\s+scaling)",
        r"(?i)(prediction\s+interval|credible\s+interval|Bayesian|MC\s+dropout|ensemble\s+uncertainty)",
    ],
    "cross_sensor_test": [
        r"(?i)(cross.?sens|multi.?sens|different\s+(camera|sens|imaging\s+platform))",
        r"(?i)(domain\s+(shift|adapt|generaliz)|cross.?domain|domain\s+gap|transfer\s+learn)",
        r"(?i)(RGB.?NIR|multispectr|hyperspectr|thermal|UAV|satellite|drone)",
    ],
    "code_available": [
        r"(?i)(https?://(github|gitlab|bitbucket|zenodo|huggingface|pypi))",
        r"(?i)(code\s+(available|release|public|open.?source))",
        r"(?i)(our\s+code|implementation\s+(is\s+)?available|supplement(ary)?\s+(material|code))",
    ],
    "dataset_role": [
        r"(?i)(we\s+(introduce|present|propose|release|collect|create|construct)\s+(a\s+)?(new\s+)?dataset)",
        r"(?i)(dataset\s+(available|download|publicly|released|published))",
        r"(?i)(using\s+(the|this|a)\s+dataset|datasets?\s+(used|employed|adopted))",
    ],
}

EVIDENCE_CHARS = 400  # context window around each match


def extract_section_hint(text, pos):
    before = text[max(0, pos - 200) : pos]
    for line in reversed(before.split("\n")):
        line = line.strip()
        if line.startswith("#") or line.startswith("##") or line.startswith("###"):
            return line[:60]
    return ""


def find_evidence(text, patterns):
    for pat in patterns:
        for m in re.finditer(pat, text):
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 100)
            ctx = text[start:end].replace("\n", " ").strip()[:EVIDENCE_CHARS]
            section = extract_section_hint(text, m.start())
            return ctx, section
    return "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    _, decisions = read_csv(repo / "data/curated/screening/full_text_decisions.csv")
    _, registry = read_csv(repo / "data/curated/fulltext/extraction_registry.csv")

    latest = {}
    for r in registry:
        pid = r.get("paper_id", "")
        if pid not in latest or r.get("created_at", "") >= latest[pid].get("created_at", ""):
            latest[pid] = r

    included = [x for x in decisions if x["decision"] in ("include_core", "include_supporting")]

    fields = [
        "paper_id", "rank", "decision", "title",
        "split_evidence", "split_section",
        "baseline_evidence", "baseline_section",
        "calibration_evidence", "calibration_section",
        "sensor_evidence", "sensor_section",
        "code_evidence", "code_section",
        "role_evidence", "role_section",
        "paper_md_path",
    ]

    seen = set()
    rows = []
    for dec in included:
        pid = dec.get("paper_id", "")
        if pid in seen:
            continue
        seen.add(pid)

        ext = latest.get(pid, {})
        od = ext.get("output_dir", "")
        pmd = repo / od / "llm" / "paper.md" if od else None

        text = ""
        if pmd and pmd.exists():
            text = pmd.read_text(encoding="utf-8")

        row = {
            "paper_id": pid,
            "rank": dec.get("rank", ""),
            "decision": dec.get("decision", ""),
            "title": dec.get("title", ""),
            "paper_md_path": str(pmd) if pmd else "",
        }

        for dim, patterns in DIMENSION_PATTERNS.items():
            ctx_key = f"{dim.split('_')[0]}_evidence"
            sec_key = f"{dim.split('_')[0]}_section"

            # Handle naming: cross_sensor_test -> sensor_evidence, dataset_role -> role_evidence
            if dim == "cross_sensor_test":
                ctx_key = "sensor_evidence"
                sec_key = "sensor_section"
            elif dim == "dataset_role":
                ctx_key = "role_evidence"
                sec_key = "role_section"

            ctx, sec = find_evidence(text, patterns)
            row[ctx_key] = ctx
            row[sec_key] = sec

        rows.append(row)

    out = repo / "outputs" / "method_gap_evidence.csv"
    atomic_write_csv(out, fields, rows)
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
