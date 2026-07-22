#!/usr/bin/env python3
"""Create a canonical paper-screening queue from provider-level edges."""
from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KEYWORDS = {
    "dataset": 2.0,
    "benchmark": 2.0,
    "agricultur": 1.5,
    "crop": 1.5,
    "weed": 2.0,
    "plant": 1.0,
    "phenotyp": 1.5,
    "segmentation": 2.0,
    "multispectral": 2.5,
    "hyperspectral": 2.5,
    "multimodal": 2.0,
    "sensor": 1.5,
    "robust": 2.0,
    "domain adaptation": 2.0,
    "uncertainty": 2.0,
    "calibration": 2.0,
    "point cloud": 1.5,
    "uav": 1.5,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).split())


def clean_doi(value: str) -> str:
    value = (value or "").strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def canonical_key(row: dict[str, str]) -> str:
    doi = clean_doi(row.get("related_doi", ""))
    if doi:
        return f"doi:{doi}"
    arxiv = normalize(row.get("related_arxiv_id", "")).replace(" ", "")
    if arxiv:
        return f"arxiv:{arxiv.removeprefix('arxiv:')}"
    pmid = normalize(row.get("related_pmid", "")).replace(" ", "")
    if pmid:
        return f"pmid:{pmid.removeprefix('pmid:')}"
    pmcid = normalize(row.get("related_pmcid", "")).replace(" ", "")
    if pmcid:
        return f"pmcid:{pmcid.removeprefix('pmcid:')}"
    title = normalize(row.get("related_title", ""))
    year = (row.get("related_year", "") or "").strip()
    if title:
        return f"titleyear:{title}:{year}"
    # Provider-only IDs are preserved in raw provenance but are too weak for
    # cross-provider canonical screening when no title or stable identifier exists.
    return ""


def best_value(rows: list[dict[str, str]], field: str) -> str:
    values = [row.get(field, "").strip() for row in rows if row.get(field, "").strip()]
    if not values:
        return ""
    # Prefer the most informative value, then stable lexical order.
    return sorted(set(values), key=lambda value: (-len(value), value.casefold()))[0]


def max_int(rows: list[dict[str, str]], field: str) -> int:
    vals: list[int] = []
    for row in rows:
        try:
            vals.append(int(float(row.get(field, ""))))
        except (TypeError, ValueError):
            continue
    return max(vals, default=0)


def parse_excluded(value: str) -> set[str]:
    if not value:
        return set()
    path = Path(value)
    if path.exists() and path.is_file():
        return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    return {part.strip() for part in value.split(",") if part.strip()}


def score_record(rows: list[dict[str, str]], title: str, abstract: str, year: str, citations: int) -> tuple[float, str]:
    directions = {row.get("direction", "") for row in rows}
    seed_ids = {row.get("seed_row_id", "") for row in rows if row.get("seed_row_id", "")}
    text = f"{title} {abstract}".casefold()
    components: list[str] = []
    score = 0.0
    if "forward_citation" in directions:
        score += 4.0
        components.append("forward:+4")
    if "backward_reference" in directions:
        score += 1.0
        components.append("backward:+1")
    try:
        y = int(year[:4])
    except (TypeError, ValueError):
        y = 0
    if y >= 2024:
        score += 3.0
        components.append("year>=2024:+3")
    elif y >= 2020:
        score += 1.0
        components.append("year>=2020:+1")
    keyword_score = sum(weight for keyword, weight in KEYWORDS.items() if keyword in text)
    keyword_score = min(keyword_score, 10.0)
    if keyword_score:
        score += keyword_score
        components.append(f"keywords:+{keyword_score:g}")
    if len(seed_ids) > 1:
        multi = min(3.0, 0.75 * (len(seed_ids) - 1))
        score += multi
        components.append(f"multi_seed:+{multi:g}")
    if citations > 0:
        citation_bonus = min(3.0, math.log10(citations + 1))
        score += citation_bonus
        components.append(f"citations:+{citation_bonus:.2f}")
    return round(score, 3), "; ".join(components)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deduplicate snowball edges into a human screening queue.")
    parser.add_argument("input", type=Path, help="snowball_edges.csv or a run directory containing it")
    parser.add_argument("--out", type=Path, required=True, help="Output CSV path or output directory")
    parser.add_argument("--exclude-seed-ids", default="", help="Comma-separated IDs or path to quarantine_seed_ids.txt")
    parser.add_argument("--min-year", type=int, default=0, help="Exclude papers older than this year (0 keeps all)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input / "snowball_edges.csv" if args.input.is_dir() else args.input
    out_csv = args.out / "screening_queue.csv" if args.out.suffix.casefold() != ".csv" else args.out
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    excluded = parse_excluded(args.exclude_seed_ids)

    rows = [row for row in read_csv(input_path) if row.get("seed_row_id", "") not in excluded]
    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    quarantined_identity_rows = 0
    for row in rows:
        key = canonical_key(row)
        if not key:
            quarantined_identity_rows += 1
            continue
        groups[key].append(row)

    records: list[dict[str, Any]] = []
    for key, group in groups.items():
        title = best_value(group, "related_title")
        year = best_value(group, "related_year")
        if args.min_year:
            try:
                if int(year[:4]) < args.min_year:
                    continue
            except (TypeError, ValueError):
                pass
        abstract = best_value(group, "abstract")
        citations = max_int(group, "related_citation_count")
        score, components = score_record(group, title, abstract, year, citations)
        providers = sorted({row.get("provider", "") for row in group if row.get("provider", "")})
        provider_ids = sorted({f"{row.get('provider','')}:{row.get('related_provider_work_id','')}" for row in group if row.get("related_provider_work_id", "")})
        seed_ids = sorted({row.get("seed_row_id", "") for row in group if row.get("seed_row_id", "")})
        dataset_names = sorted({row.get("dataset_name", "") for row in group if row.get("dataset_name", "")})
        directions = sorted({row.get("direction", "") for row in group if row.get("direction", "")})
        records.append({
            "canonical_paper_id": key,
            "priority_score": score,
            "priority_components": components,
            "title": title,
            "year": year,
            "publication_date": best_value(group, "related_publication_date"),
            "authors": best_value(group, "related_authors"),
            "venue": best_value(group, "related_venue"),
            "journal": best_value(group, "related_journal"),
            "doi": clean_doi(best_value(group, "related_doi")),
            "arxiv_id": best_value(group, "related_arxiv_id"),
            "pmid": best_value(group, "related_pmid"),
            "pmcid": best_value(group, "related_pmcid"),
            "landing_url": best_value(group, "related_url"),
            "pdf_url": best_value(group, "related_pdf_url"),
            "is_open_access": best_value(group, "related_is_open_access"),
            "max_provider_citation_count": citations,
            "max_provider_reference_count": max_int(group, "related_reference_count"),
            "providers": "; ".join(providers),
            "provider_ids": "; ".join(provider_ids),
            "seed_ids": "; ".join(seed_ids),
            "dataset_names": "; ".join(dataset_names),
            "directions": "; ".join(directions),
            "provider_edge_rows": len(group),
            "abstract": abstract,
            # Human review fields intentionally blank.
            "title_abstract_decision": "",
            "full_text_decision": "",
            "paper_role": "",
            "actual_dataset_use": "",
            "dataset_use_evidence": "",
            "exclusion_reason": "",
            "reviewer": "",
            "reviewed_date": "",
            "notes": "",
        })

    records.sort(key=lambda row: (-float(row["priority_score"]), -int(row["year"][:4]) if str(row["year"])[:4].isdigit() else 0, str(row["title"]).casefold()))
    for index, record in enumerate(records, start=1):
        record["screening_rank"] = index

    fields = [
        "screening_rank", "canonical_paper_id", "priority_score", "priority_components", "title", "year",
        "publication_date", "authors", "venue", "journal", "doi", "arxiv_id", "pmid", "pmcid",
        "landing_url", "pdf_url", "is_open_access", "max_provider_citation_count", "max_provider_reference_count",
        "providers", "provider_ids", "seed_ids", "dataset_names", "directions", "provider_edge_rows", "abstract",
        "title_abstract_decision", "full_text_decision", "paper_role", "actual_dataset_use", "dataset_use_evidence",
        "exclusion_reason", "reviewer", "reviewed_date", "notes",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    summary_path = out_csv.with_name(out_csv.stem + "_summary.md")
    summary_path.write_text(
        "\n".join([
            "# Screening queue generation summary",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Input: `{input_path}`",
            f"Output: `{out_csv}`",
            f"Provider edge rows read: {len(rows)}",
            f"Canonical paper rows written: {len(records)}",
            f"Excluded seed IDs: `{', '.join(sorted(excluded)) or 'none'}`",
            f"Identity-empty rows quarantined: {quarantined_identity_rows}",
            "",
            "Priority scores are triage aids, not inclusion decisions. A paper counts as dataset use only after evidence is verified from the paper.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} canonical papers to {out_csv}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
