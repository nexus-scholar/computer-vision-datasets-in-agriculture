#!/usr/bin/env python3
"""Auditable full-text evidence-priority workflow.

The workflow has two layers:

1. A deterministic bootstrap ranks every active title/abstract inclusion from
   already-curated metadata and project rules.
2. Optional, bounded AI semantic scores refine the bootstrap in append-only
   batches. Unscored papers remain in the queue using bootstrap values.

Python owns identity joins, validation, normalization, weighting, sensitivity
analysis, diversity reranking, manifests, and evaluation. Models only provide
bounded semantic judgments.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import statistics
import sys
import tomllib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

PROTOCOL = "EVIDENCE_ROI_V1"
SCORE_FIELDS = [
    "score_id", "candidate_id", "included_order", "original_screening_rank", "title",
    "project_fit", "dataset_evidence_value", "method_gap_value", "decision_leverage",
    "actual_use_likelihood", "evidence_specificity", "information_uncertainty",
    "estimated_reading_cost", "primary_role", "primary_theme", "dataset_cluster",
    "task_cluster", "modality_cluster", "score_confidence", "evidence_note", "reviewer",
    "model", "protocol_version", "scored_at", "supersedes_score_id", "notes",
]
BATCH_FIELDS = [
    "batch_id", "priority_position_start", "priority_position_end", "candidate_count",
    "input_rows_path", "input_rows_sha256", "scored_rows_path", "scored_rows_sha256",
    "source_decisions_path", "source_decisions_sha256", "source_queue_path",
    "source_queue_sha256", "source_ranking_path", "source_ranking_sha256",
    "protocol_version", "reviewer", "model", "completed_at", "validation_status", "notes",
]
ROLES = {
    "dataset_introduction", "dataset_extension", "experimental_dataset_use",
    "benchmark_or_challenge", "robustness_or_reliability_method",
    "multimodal_or_sensor_method", "domain_adaptation_method",
    "foundation_model_study", "segmentation_method", "3d_or_phenotyping_method",
    "survey_or_review", "contextual_background", "other",
}
THEMES = {
    "multispectral_reliability", "crop_weed_segmentation", "plant_disease_segmentation",
    "dataset_quality_and_benchmarking", "multimodal_fusion", "missing_modality",
    "cross_sensor_or_domain_shift", "uncertainty_and_calibration", "foundation_models",
    "remote_sensing_uav", "orchard_robotics", "3d_phenotyping",
    "temporal_phenotyping", "other",
}
CONFIDENCE = {"high", "medium", "low"}
RELATIONSHIP_PRIOR = {
    "introduces_dataset": 1.00,
    "extends_dataset": 0.95,
    "benchmarks_dataset": 0.90,
    "uses_dataset_experimentally": 0.85,
    "pretrains_on_dataset": 0.80,
    "compares_datasets": 0.72,
    "mentions_dataset_only": 0.25,
    "no_dataset_relationship": 0.10,
    "unclear": 0.45,
}
DIRECT_PROJECT_TAGS = {
    "multispectral", "multimodal", "cross_sensor", "missing_modality",
    "corrupted_input", "uncertainty", "calibration", "failure_detection",
    "domain_adaptation", "semantic_segmentation",
}
RELIABILITY_TAGS = {
    "cross_sensor", "missing_modality", "corrupted_input", "uncertainty",
    "calibration", "failure_detection",
}
ADJACENT_PROJECT_TAGS = {
    "instance_segmentation", "panoptic_segmentation", "foundation_models",
    "3d_vision", "lidar_or_point_cloud", "remote_sensing", "uav", "robotics",
    "phenotyping", "multitemporal", "hyperspectral", "thermal", "depth_or_rgbd",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def short_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    tmp.replace(path)


def append_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    existing = read_csv(path)
    write_csv(path, [*existing, *rows], fieldnames)


def load_config(repo: Path, path: str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else repo / "config/fulltext_ranking.toml"
    if not config_path.is_absolute():
        config_path = repo / config_path
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    required = [
        ("weights.science", config.get("weights", {}).get("science", {})),
        ("weights.feasibility", config.get("weights", {}).get("feasibility", {})),
        ("weights.recommended", config.get("weights", {}).get("recommended", {})),
        ("weights.base", config.get("weights", {}).get("base", {})),
    ]
    for name, weights in required:
        total = sum(float(value) for value in weights.values())
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"{name} must sum to 1.0; got {total:.8f}")
    if config.get("policy", {}).get("allow_automatic_exclusion", False):
        raise ValueError("Ranking policy may not automatically exclude included papers")


def discover_file(repo: Path, pattern: str, filename: str) -> Path:
    matches = [p / filename for p in repo.glob(pattern) if (p / filename).exists()]
    if not matches:
        raise FileNotFoundError(f"No {filename} found under pattern {pattern}")
    return sorted(matches, key=lambda p: p.parent.name)[-1]


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def split_tokens(value: str) -> list[str]:
    return [token.strip() for token in re.split(r"[;|]", value or "") if token.strip()]


def normalized_token(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return value or "unknown"


def stable_id_count(row: dict[str, str]) -> int:
    count = 0
    for key in ("doi", "arxiv_id", "pmid", "pmcid"):
        if row.get(key, "").strip():
            count += 1
    if row.get("provider_ids", "").strip():
        count += 1
    return count


def extraction_ease(row: dict[str, str], acquired: bool) -> float:
    if acquired:
        base = 0.90
    elif row.get("pmcid", "").strip():
        base = 0.88
    elif row.get("arxiv_id", "").strip() or row.get("pdf_url", "").strip():
        base = 0.78
    elif row.get("doi", "").strip():
        base = 0.60
    else:
        base = 0.40
    text = " ".join([
        row.get("likely_paper_type", ""), row.get("vision_task", ""),
        row.get("modalities", ""), row.get("abstract", ""), row.get("title", ""),
    ]).lower()
    if any(term in text for term in ("survey", "systematic review", "hyperspectral", "point cloud", "3d", "multimodal")):
        base -= 0.10
    return max(0.10, min(1.0, base))


def legal_access_score(row: dict[str, str], acquired: bool) -> float:
    if acquired:
        return 1.0
    if row.get("pmcid", "").strip() or row.get("arxiv_id", "").strip():
        return 0.95
    if parse_bool(row.get("is_open_access", "")) and row.get("pdf_url", "").strip():
        return 0.95
    if row.get("pdf_url", "").strip():
        return 0.78
    if parse_bool(row.get("is_open_access", "")):
        return 0.72
    if row.get("doi", "").strip():
        return 0.45
    return 0.20


def active_artifacts(repo: Path) -> set[str]:
    path = repo / "data/curated/fulltext/artifact_registry.csv"
    result: set[str] = set()
    for row in read_csv(path):
        status = (row.get("status") or row.get("artifact_status") or "").strip().lower()
        if status in {"success", "validated", "manual_import", "available"}:
            paper_id = (row.get("paper_id") or row.get("candidate_id") or "").strip()
            if paper_id:
                result.add(paper_id)
    return result


def build_candidates(repo: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], Path, Path]:
    decisions_path = repo / "data/curated/screening/title_abstract_decisions.csv"
    queue_path = discover_file(repo, "outputs/screening_queue_*", "screening_queue.csv")
    decisions = read_csv(decisions_path)
    queue_rows = read_csv(queue_path)
    queue = {row.get("canonical_paper_id", ""): row for row in queue_rows}
    acquired = active_artifacts(repo)
    current_year = int(config["project"].get("current_year", datetime.now().year))
    included = sorted(
        (row for row in decisions if row.get("decision") == "include"),
        key=lambda row: parse_int(row.get("rank", ""), 10**9),
    )
    candidates: list[dict[str, Any]] = []
    for order, decision in enumerate(included, start=1):
        candidate_id = decision.get("candidate_id", "").strip()
        q = queue.get(candidate_id)
        if q is None:
            raise ValueError(f"Included candidate missing from frozen queue: {candidate_id}")
        year = parse_int(q.get("year", ""), current_year)
        age = max(1, current_year - year + 1)
        citations = parse_int(q.get("max_provider_citation_count", ""), 0)
        citation_velocity = math.log1p(max(0, citations)) / (age ** 0.70)
        seeds = sorted(set(split_tokens(q.get("seed_ids", ""))))
        datasets = sorted(set(split_tokens(decision.get("named_datasets", "")) + split_tokens(q.get("dataset_names", ""))))
        datasets = [value for value in datasets if value.lower() not in {"unknown", "none", "n/a"}]
        edge_rows = parse_int(q.get("provider_edge_rows", ""), 0)
        network_breadth = len(seeds) + math.log1p(max(0, edge_rows))
        abstract = q.get("abstract", "") or ""
        acquired_flag = candidate_id in acquired
        identifiers = stable_id_count(q)
        candidates.append({
            "included_order": order,
            "candidate_id": candidate_id,
            "original_screening_rank": parse_int(decision.get("rank", "")),
            "title": decision.get("title", "") or q.get("title", ""),
            "year": year,
            "publication_date": q.get("publication_date", ""),
            "authors": q.get("authors", ""),
            "venue": q.get("venue", ""),
            "journal": q.get("journal", ""),
            "doi": q.get("doi", ""),
            "arxiv_id": q.get("arxiv_id", ""),
            "pmid": q.get("pmid", ""),
            "pmcid": q.get("pmcid", ""),
            "landing_url": q.get("landing_url", ""),
            "pdf_url": q.get("pdf_url", ""),
            "is_open_access": q.get("is_open_access", ""),
            "citation_count": citations,
            "reference_count": parse_int(q.get("max_provider_reference_count", ""), 0),
            "providers": q.get("providers", ""),
            "provider_ids": q.get("provider_ids", ""),
            "seed_ids": ";".join(seeds),
            "dataset_names": ";".join(datasets) if datasets else "unknown",
            "directions": q.get("directions", ""),
            "provider_edge_rows": edge_rows,
            "abstract": abstract,
            "decision_confidence": decision.get("decision_confidence", ""),
            "likely_paper_type": decision.get("likely_paper_type", ""),
            "likely_dataset_relationship": decision.get("likely_dataset_relationship", ""),
            "agricultural_domain": decision.get("agricultural_domain", ""),
            "vision_task": decision.get("vision_task", ""),
            "modalities": decision.get("modalities", ""),
            "relevance_yes": decision.get("relevance_yes", ""),
            "relevance_unclear": decision.get("relevance_unclear", ""),
            "reason_code": decision.get("reason_code", ""),
            "reason_note": decision.get("reason_note", ""),
            "abstract_available": decision.get("abstract_available", ""),
            "full_text_available": decision.get("full_text_available", ""),
            "has_acquired_fulltext": "yes" if acquired_flag else "no",
            "det_legal_access": round(legal_access_score(q, acquired_flag), 6),
            "det_identifier_completeness": round(min(1.0, identifiers / 4.0), 6),
            "det_abstract_completeness": round(min(1.0, len(abstract.strip()) / 1500.0), 6),
            "det_extraction_ease": round(extraction_ease({**q, **decision}, acquired_flag), 6),
            "det_network_breadth_raw": round(network_breadth, 6),
            "det_citation_velocity_raw": round(citation_velocity, 6),
            "det_recency_raw": round(max(0.0, min(1.0, (year - 2018) / 8.0)), 6),
            "det_relationship_prior": round(RELATIONSHIP_PRIOR.get(decision.get("likely_dataset_relationship", ""), 0.40), 6),
        })
    if len({row["candidate_id"] for row in candidates}) != len(candidates):
        raise ValueError("Active include set contains duplicate candidate IDs")
    return candidates, decisions_path, queue_path


def relevance_tags(candidate: dict[str, Any]) -> set[str]:
    tags = {normalized_token(token) for token in split_tokens(str(candidate.get("relevance_yes", "")))}
    text = " ".join([
        str(candidate.get("vision_task", "")), str(candidate.get("modalities", "")),
        str(candidate.get("likely_paper_type", "")), str(candidate.get("likely_dataset_relationship", "")),
        str(candidate.get("title", "")), str(candidate.get("reason_note", "")),
    ]).lower()
    aliases = {
        "semantic segmentation": "semantic_segmentation",
        "instance segmentation": "instance_segmentation",
        "panoptic": "panoptic_segmentation",
        "multispectral": "multispectral",
        "hyperspectral": "hyperspectral",
        "multimodal": "multimodal",
        "multi-modal": "multimodal",
        "domain adaptation": "domain_adaptation",
        "cross-sensor": "cross_sensor",
        "sensor shift": "cross_sensor",
        "missing modality": "missing_modality",
        "missing band": "missing_modality",
        "corrupt": "corrupted_input",
        "uncertainty": "uncertainty",
        "calibration": "calibration",
        "failure detection": "failure_detection",
        "foundation model": "foundation_models",
        "sam": "foundation_models",
        "point cloud": "lidar_or_point_cloud",
        "3d": "3d_vision",
        "uav": "uav",
        "remote sensing": "remote_sensing",
        "robot": "robotics",
        "phenotyp": "phenotyping",
        "temporal": "multitemporal",
        "tracking": "tracking",
        "thermal": "thermal",
        "depth": "depth_or_rgbd",
    }
    for needle, tag in aliases.items():
        if needle in text:
            tags.add(tag)
    return tags


def infer_role(candidate: dict[str, Any], tags: set[str]) -> str:
    relation = str(candidate.get("likely_dataset_relationship", ""))
    paper_type = str(candidate.get("likely_paper_type", ""))
    if relation == "introduces_dataset" or paper_type == "dataset_paper":
        return "dataset_introduction"
    if relation == "extends_dataset" or paper_type == "dataset_extension":
        return "dataset_extension"
    if relation == "benchmarks_dataset" or paper_type == "benchmark_or_challenge":
        return "benchmark_or_challenge"
    if RELIABILITY_TAGS & tags:
        return "robustness_or_reliability_method"
    if {"multimodal", "multispectral", "hyperspectral", "thermal", "depth_or_rgbd", "lidar_or_point_cloud"} & tags:
        return "multimodal_or_sensor_method"
    if "domain_adaptation" in tags:
        return "domain_adaptation_method"
    if "foundation_models" in tags:
        return "foundation_model_study"
    if {"3d_vision", "phenotyping", "lidar_or_point_cloud"} & tags:
        return "3d_or_phenotyping_method"
    if {"semantic_segmentation", "instance_segmentation", "panoptic_segmentation"} & tags:
        return "segmentation_method"
    if paper_type in {"survey_or_review", "survey", "review"}:
        return "survey_or_review"
    if relation in {"uses_dataset_experimentally", "pretrains_on_dataset", "compares_datasets"}:
        return "experimental_dataset_use"
    return "contextual_background"


def infer_theme(candidate: dict[str, Any], tags: set[str]) -> str:
    text = " ".join([
        str(candidate.get("title", "")), str(candidate.get("agricultural_domain", "")),
        str(candidate.get("vision_task", "")), str(candidate.get("dataset_names", "")),
    ]).lower()
    if "missing_modality" in tags:
        return "missing_modality"
    if {"uncertainty", "calibration", "failure_detection"} & tags:
        return "uncertainty_and_calibration"
    if "cross_sensor" in tags or "domain_adaptation" in tags:
        return "cross_sensor_or_domain_shift"
    if "multispectral" in tags:
        return "multispectral_reliability"
    if "multimodal" in tags or {"thermal", "depth_or_rgbd", "lidar_or_point_cloud", "hyperspectral"} & tags:
        return "multimodal_fusion"
    if "foundation_models" in tags:
        return "foundation_models"
    if {"remote_sensing", "uav"} & tags:
        return "remote_sensing_uav"
    if "robotics" in tags or "orchard" in text or "harvest" in text:
        return "orchard_robotics"
    if {"3d_vision", "lidar_or_point_cloud"} & tags:
        return "3d_phenotyping"
    if "multitemporal" in tags or "tracking" in tags:
        return "temporal_phenotyping"
    if "disease" in text and "semantic_segmentation" in tags:
        return "plant_disease_segmentation"
    if any(term in text for term in ("weed", "crop")) and "semantic_segmentation" in tags:
        return "crop_weed_segmentation"
    if str(candidate.get("likely_dataset_relationship", "")) in {"introduces_dataset", "extends_dataset", "benchmarks_dataset"}:
        return "dataset_quality_and_benchmarking"
    return "other"


def first_cluster(value: str) -> str:
    tokens = [normalized_token(token) for token in split_tokens(value) if normalized_token(token) != "unknown"]
    return tokens[0] if tokens else "unknown"


def bootstrap_semantic(candidate: dict[str, Any]) -> dict[str, Any]:
    tags = relevance_tags(candidate)
    direct_count = len(DIRECT_PROJECT_TAGS & tags)
    reliable_count = len(RELIABILITY_TAGS & tags)
    adjacent_count = len(ADJACENT_PROJECT_TAGS & tags)
    relation = str(candidate.get("likely_dataset_relationship", ""))
    paper_type = str(candidate.get("likely_paper_type", ""))
    abstract = str(candidate.get("abstract", ""))
    named_dataset = str(candidate.get("dataset_names", "")) not in {"", "unknown"}

    if reliable_count >= 1 and direct_count >= 2:
        project_fit = 4
    elif direct_count >= 1 or adjacent_count >= 2:
        project_fit = 3
    elif relation != "no_dataset_relationship" or paper_type not in {"", "other", "unclear"}:
        project_fit = 2
    else:
        project_fit = 1

    dataset_value = {
        "introduces_dataset": 4,
        "extends_dataset": 4,
        "benchmarks_dataset": 3,
        "uses_dataset_experimentally": 3,
        "pretrains_on_dataset": 3,
        "compares_datasets": 2,
        "mentions_dataset_only": 1,
        "no_dataset_relationship": 0,
        "unclear": 2,
    }.get(relation, 2)

    if reliable_count >= 1:
        method_gap = 4
    elif {"multimodal", "multispectral", "domain_adaptation", "foundation_models", "3d_vision", "lidar_or_point_cloud"} & tags:
        method_gap = 3
    elif {"semantic_segmentation", "instance_segmentation", "panoptic_segmentation"} & tags:
        method_gap = 2
    else:
        method_gap = 1

    if project_fit == 4 and (dataset_value >= 3 or method_gap >= 4):
        leverage = 4
    elif dataset_value >= 3 or method_gap >= 3:
        leverage = 3
    elif project_fit >= 2:
        leverage = 2
    else:
        leverage = 1

    actual_use = {
        "uses_dataset_experimentally": 4,
        "benchmarks_dataset": 4,
        "pretrains_on_dataset": 4,
        "extends_dataset": 3,
        "compares_datasets": 3,
        "introduces_dataset": 2,
        "unclear": 2,
        "mentions_dataset_only": 1,
        "no_dataset_relationship": 0,
    }.get(relation, 1)

    numeric_mentions = len(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", abstract))
    specificity = 0
    if abstract.strip():
        specificity += 1
    if len(abstract) >= 600:
        specificity += 1
    if numeric_mentions >= 2 or named_dataset:
        specificity += 1
    if numeric_mentions >= 5 or any(term in abstract.lower() for term in ("benchmark", "mIoU", "dice", "accuracy", "dataset contains", "images")):
        specificity += 1
    specificity = min(4, specificity)

    uncertainty = 1
    if str(candidate.get("decision_confidence", "")).lower() == "medium":
        uncertainty += 1
    if str(candidate.get("decision_confidence", "")).lower() == "low":
        uncertainty += 2
    if str(candidate.get("relevance_unclear", "")).strip():
        uncertainty += 1
    if relation in {"unclear", "uses_dataset_experimentally", "benchmarks_dataset"} and not named_dataset:
        uncertainty += 1
    if not abstract.strip():
        uncertainty += 1
    uncertainty = min(4, uncertainty)

    cost = 2
    text = " ".join([candidate.get("title", ""), paper_type, candidate.get("modalities", ""), candidate.get("vision_task", "")]).lower()
    if paper_type in {"survey_or_review", "survey", "review"}:
        cost += 1
    if any(term in text for term in ("hyperspectral", "point cloud", "3d", "multimodal", "multi-modal", "supplement")):
        cost += 1
    if not candidate.get("pdf_url") and not candidate.get("pmcid") and not candidate.get("arxiv_id"):
        cost += 1
    cost = max(1, min(5, cost))

    role = infer_role(candidate, tags)
    theme = infer_theme(candidate, tags)
    dataset_cluster = first_cluster(str(candidate.get("dataset_names", "")))
    task_cluster = first_cluster(str(candidate.get("vision_task", "")))
    modality_cluster = first_cluster(str(candidate.get("modalities", "")))
    evidence_note = (
        f"Bootstrap from curated relationship={relation or 'unknown'}, role={role}, "
        f"theme={theme}, direct_project_tags={','.join(sorted(DIRECT_PROJECT_TAGS & tags)) or 'none'}."
    )
    return {
        "project_fit": str(project_fit),
        "dataset_evidence_value": str(dataset_value),
        "method_gap_value": str(method_gap),
        "decision_leverage": str(leverage),
        "actual_use_likelihood": str(actual_use),
        "evidence_specificity": str(specificity),
        "information_uncertainty": str(uncertainty),
        "estimated_reading_cost": str(cost),
        "primary_role": role,
        "primary_theme": theme,
        "dataset_cluster": dataset_cluster,
        "task_cluster": task_cluster,
        "modality_cluster": modality_cluster,
        "score_confidence": "low",
        "evidence_note": evidence_note,
        "reviewer": "deterministic_bootstrap",
        "model": "none",
        "protocol_version": PROTOCOL,
        "scored_at": "",
        "supersedes_score_id": "",
        "notes": "Bootstrap scheduling estimate; not curated semantic evidence.",
    }


def parse_range(value: str | None, maximum: int, default_size: int = 20) -> tuple[int, int]:
    if value and value.strip():
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", value.strip())
        if not match:
            raise ValueError("Range must be N or N-M using unscored priority positions")
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
    else:
        start, end = 1, min(maximum, default_size)
    if start < 1 or end < start or end > maximum:
        raise ValueError(f"Range {start}-{end} is outside 1-{maximum}")
    if end - start + 1 > 20:
        raise ValueError("A semantic-scoring batch may contain at most 20 papers")
    return start, end


def active_scores(repo: Path) -> list[dict[str, str]]:
    return read_csv(repo / "data/curated/ranking/paper_priority_scores.csv")


def refresh_active_scores(repo: Path) -> list[dict[str, str]]:
    history_path = repo / "data/curated/ranking/paper_priority_score_history.csv"
    history = read_csv(history_path)
    latest: dict[str, dict[str, str]] = {}
    for row in history:
        candidate = row.get("candidate_id", "")
        previous = latest.get(candidate)
        if previous is None or (row.get("scored_at", ""), row.get("score_id", "")) >= (previous.get("scored_at", ""), previous.get("score_id", "")):
            latest[candidate] = row
    rows = sorted(latest.values(), key=lambda row: parse_int(row.get("included_order", ""), 10**9))
    write_csv(repo / "data/curated/ranking/paper_priority_scores.csv", rows, SCORE_FIELDS)
    return rows


def percentile(values: list[float]) -> list[float]:
    if not values:
        return []
    sorted_values = sorted(values)
    n = len(values)
    if n == 1:
        return [0.5]
    positions: dict[float, list[int]] = defaultdict(list)
    for index, value in enumerate(sorted_values):
        positions[value].append(index)
    ranks = {value: sum(indices) / len(indices) / (n - 1) for value, indices in positions.items()}
    return [ranks[value] for value in values]


def weighted_sum(weights: dict[str, float], values: dict[str, float]) -> float:
    return sum(float(weights.get(key, 0.0)) * float(values.get(key, 0.0)) for key in weights)


def tag_set(row: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    for prefix, value in (
        ("role", row.get("primary_role", "")),
        ("theme", row.get("primary_theme", "")),
        ("dataset_cluster", row.get("dataset_cluster", "")),
        ("task", row.get("task_cluster", "")),
        ("modality", row.get("modality_cluster", "")),
    ):
        if value and value != "unknown":
            tags.add(f"{prefix}:{str(value).lower().strip()}")
    for token in split_tokens(str(row.get("dataset_names", ""))):
        if token.lower() != "unknown":
            tags.add(f"dataset:{token.lower()}")
    for token in split_tokens(str(row.get("seed_ids", ""))):
        tags.add(f"seed:{token.lower()}")
    return tags


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def diversity_rerank(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    settings = config["diversity"]
    lam = float(settings.get("mmr_lambda", 0.78))
    first_window = int(settings.get("first_window", 20))
    max_dataset = int(settings.get("max_same_dataset_first_window", 3))
    max_theme = int(settings.get("max_same_theme_first_window", 6))
    penalty_weight = float(settings.get("quota_penalty", 0.05))
    pinned = list(config.get("policy", {}).get("pinned_candidate_ids", []))
    by_id = {row["candidate_id"]: row for row in rows}
    selected: list[dict[str, Any]] = []
    remaining = dict(by_id)
    for candidate_id in pinned:
        if candidate_id in remaining:
            selected.append(remaining.pop(candidate_id))
    dataset_counts: Counter[str] = Counter()
    theme_counts: Counter[str] = Counter()
    for row in selected:
        if row.get("dataset_cluster") not in ("", "unknown"):
            dataset_counts[str(row["dataset_cluster"])] += 1
        if row.get("primary_theme") not in ("", "unknown"):
            theme_counts[str(row["primary_theme"])] += 1
    while remaining:
        best_id: str | None = None
        best_tuple: tuple[float, float, int] | None = None
        for candidate_id, row in remaining.items():
            relevance = float(row["base_priority_score"]) / 100.0
            tags = row["_tags"]
            max_similarity = max((jaccard(tags, chosen["_tags"]) for chosen in selected), default=0.0)
            diversity = 1.0 - max_similarity
            score = lam * relevance + (1.0 - lam) * diversity
            if len(selected) < first_window:
                dataset = str(row.get("dataset_cluster", ""))
                theme = str(row.get("primary_theme", ""))
                if dataset not in ("", "unknown") and dataset_counts[dataset] >= max_dataset:
                    score -= penalty_weight * (dataset_counts[dataset] - max_dataset + 1)
                if theme not in ("", "unknown") and theme_counts[theme] >= max_theme:
                    score -= penalty_weight * (theme_counts[theme] - max_theme + 1)
            tie = (score, relevance, -int(row["included_order"]))
            if best_tuple is None or tie > best_tuple:
                best_tuple = tie
                best_id = candidate_id
        assert best_id is not None
        chosen = remaining.pop(best_id)
        chosen["mmr_selection_score"] = round((best_tuple or (0.0, 0.0, 0))[0] * 100.0, 6)
        selected.append(chosen)
        dataset = str(chosen.get("dataset_cluster", ""))
        theme = str(chosen.get("primary_theme", ""))
        if dataset not in ("", "unknown"):
            dataset_counts[dataset] += 1
        if theme not in ("", "unknown"):
            theme_counts[theme] += 1
    return selected


def rank_positions(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    ordered = sorted(rows, key=lambda row: (-float(row[field]), int(row["included_order"])))
    return {row["candidate_id"]: index for index, row in enumerate(ordered, start=1)}


def normalized_weight_sample(base: dict[str, float], rng: random.Random, sigma: float) -> dict[str, float]:
    sampled = {key: max(1e-9, float(value) * math.exp(rng.gauss(0.0, sigma))) for key, value in base.items()}
    total = sum(sampled.values())
    return {key: value / total for key, value in sampled.items()}


def sensitivity_analysis(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    settings = config.get("sensitivity", {})
    simulations = int(settings.get("simulations", 500))
    seed = int(settings.get("seed", 20260722))
    weight_sigma = float(settings.get("weight_lognormal_sigma", 0.18))
    score_sigma_ai = float(settings.get("semantic_score_sigma_ai", 0.05))
    score_sigma_bootstrap = float(settings.get("semantic_score_sigma_bootstrap", 0.12))
    rng = random.Random(seed)
    rank_samples: dict[str, list[int]] = {row["candidate_id"]: [] for row in rows}

    for _ in range(simulations):
        science_weights = normalized_weight_sample(config["weights"]["science"], rng, weight_sigma)
        feasibility_weights = normalized_weight_sample(config["weights"]["feasibility"], rng, weight_sigma)
        recommended_weights = normalized_weight_sample(config["weights"]["recommended"], rng, weight_sigma)
        base_weights = normalized_weight_sample(config["weights"]["base"], rng, weight_sigma)
        scores: list[tuple[str, float, int]] = []
        for row in rows:
            source = str(row.get("semantic_score_source", "bootstrap"))
            semantic_sigma = score_sigma_ai if source == "ai" else score_sigma_bootstrap
            semantic: dict[str, float] = {}
            for field in (
                "project_fit", "dataset_evidence_value", "method_gap_value", "decision_leverage",
                "actual_use_likelihood", "evidence_specificity", "information_uncertainty",
            ):
                base_value = parse_int(str(row.get(field, "0"))) / 4.0
                semantic[field] = min(1.0, max(0.0, base_value + rng.gauss(0.0, semantic_sigma)))
            science_values = {
                **semantic,
                "network_breadth": float(row["norm_network_breadth"]),
                "citation_velocity": float(row["norm_citation_velocity"]),
                "recency": float(row["norm_recency"]),
            }
            science = 100.0 * weighted_sum(science_weights, science_values)
            feasibility_values = {
                "legal_access": float(row["det_legal_access"]),
                "identifier_completeness": float(row["det_identifier_completeness"]),
                "abstract_completeness": float(row["det_abstract_completeness"]),
                "extraction_ease": float(row["det_extraction_ease"]),
            }
            feasibility = 100.0 * weighted_sum(feasibility_weights, feasibility_values)
            info_parts = [semantic["project_fit"], semantic["decision_leverage"], semantic["information_uncertainty"]]
            information_gain = 100.0 * (math.prod(info_parts) ** (1.0 / 3.0) if all(info_parts) else 0.0)
            strategic = weighted_sum(recommended_weights, {
                "science": science,
                "information_gain": information_gain,
                "feasibility": feasibility,
            })
            cost_norm = parse_int(str(row.get("estimated_reading_cost", "3")), 3) / 5.0
            roi_cfg = config["roi"]
            fast_roi = science * (
                float(roi_cfg.get("feasibility_floor", 0.55))
                + float(roi_cfg.get("feasibility_span", 0.45)) * feasibility / 100.0
            ) / (
                float(roi_cfg.get("cost_floor", 0.65))
                + float(roi_cfg.get("cost_span", 0.35)) * cost_norm
            )
            fast_roi = max(0.0, min(100.0, fast_roi))
            base_priority = weighted_sum(base_weights, {"strategic": strategic, "fast_roi": fast_roi})
            scores.append((row["candidate_id"], base_priority, int(row["included_order"])))
        ordered = sorted(scores, key=lambda item: (-item[1], item[2]))
        for rank, (candidate_id, _, _) in enumerate(ordered, start=1):
            rank_samples[candidate_id].append(rank)

    result: dict[str, dict[str, Any]] = {}
    for candidate_id, samples in rank_samples.items():
        mean_rank = statistics.fmean(samples)
        median_rank = statistics.median(samples)
        rank_sd = statistics.pstdev(samples) if len(samples) > 1 else 0.0
        if rank_sd <= 5:
            stability = "stable"
        elif rank_sd <= 15:
            stability = "moderate"
        else:
            stability = "unstable"
        result[candidate_id] = {
            "sensitivity_mean_rank": round(mean_rank, 6),
            "sensitivity_median_rank": round(float(median_rank), 6),
            "sensitivity_rank_sd": round(rank_sd, 6),
            "sensitivity_p_top20": round(sum(rank <= 20 for rank in samples) / len(samples), 6),
            "sensitivity_p_top40": round(sum(rank <= 40 for rank in samples) / len(samples), 6),
            "sensitivity_p_top80": round(sum(rank <= 80 for rank in samples) / len(samples), 6),
            "rank_stability": stability,
        }
    return result


def pareto_layers(rows: list[dict[str, Any]]) -> dict[str, int]:
    remaining = list(rows)
    layers: dict[str, int] = {}
    layer = 1
    while remaining:
        frontier: list[dict[str, Any]] = []
        for candidate in remaining:
            dominated = False
            for other in remaining:
                if other is candidate:
                    continue
                at_least = (
                    float(other["science_score"]) >= float(candidate["science_score"])
                    and float(other["information_gain_score"]) >= float(candidate["information_gain_score"])
                    and float(other["feasibility_score"]) >= float(candidate["feasibility_score"])
                )
                strict = (
                    float(other["science_score"]) > float(candidate["science_score"])
                    or float(other["information_gain_score"]) > float(candidate["information_gain_score"])
                    or float(other["feasibility_score"]) > float(candidate["feasibility_score"])
                )
                if at_least and strict:
                    dominated = True
                    break
            if not dominated:
                frontier.append(candidate)
        if not frontier:  # defensive; should be impossible
            frontier = [remaining[0]]
        frontier_ids = {row["candidate_id"] for row in frontier}
        for row in frontier:
            layers[row["candidate_id"]] = layer
        remaining = [row for row in remaining if row["candidate_id"] not in frontier_ids]
        layer += 1
    return layers


def build_rank_rows(
    repo: Path,
    config: dict[str, Any],
    mode: str = "hybrid",
    with_sensitivity: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Path, Path]:
    candidates, decisions_path, queue_path = build_candidates(repo, config)
    ai_scores = {row["candidate_id"]: row for row in refresh_active_scores(repo)} if mode == "hybrid" else {}
    raw = {
        "network_breadth": [float(row["det_network_breadth_raw"]) for row in candidates],
        "citation_velocity": [float(row["det_citation_velocity_raw"]) for row in candidates],
        "recency": [float(row["det_recency_raw"]) for row in candidates],
    }
    normalized = {key: percentile(values) for key, values in raw.items()}
    science_weights = config["weights"]["science"]
    feasibility_weights = config["weights"]["feasibility"]
    recommended_weights = config["weights"]["recommended"]
    base_weights = config["weights"]["base"]
    roi_cfg = config["roi"]
    rows: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates):
        score = ai_scores.get(candidate["candidate_id"])
        source = "ai" if score is not None else "bootstrap"
        semantic_row = score if score is not None else bootstrap_semantic(candidate)
        semantic = {
            "project_fit": parse_int(semantic_row.get("project_fit", "0")) / 4.0,
            "dataset_evidence_value": parse_int(semantic_row.get("dataset_evidence_value", "0")) / 4.0,
            "method_gap_value": parse_int(semantic_row.get("method_gap_value", "0")) / 4.0,
            "decision_leverage": parse_int(semantic_row.get("decision_leverage", "0")) / 4.0,
            "actual_use_likelihood": parse_int(semantic_row.get("actual_use_likelihood", "0")) / 4.0,
            "evidence_specificity": parse_int(semantic_row.get("evidence_specificity", "0")) / 4.0,
            "information_uncertainty": parse_int(semantic_row.get("information_uncertainty", "0")) / 4.0,
        }
        science_values = {
            **semantic,
            "network_breadth": normalized["network_breadth"][index],
            "citation_velocity": normalized["citation_velocity"][index],
            "recency": normalized["recency"][index],
        }
        science = 100.0 * weighted_sum(science_weights, science_values)
        feasibility_values = {
            "legal_access": float(candidate["det_legal_access"]),
            "identifier_completeness": float(candidate["det_identifier_completeness"]),
            "abstract_completeness": float(candidate["det_abstract_completeness"]),
            "extraction_ease": float(candidate["det_extraction_ease"]),
        }
        feasibility = 100.0 * weighted_sum(feasibility_weights, feasibility_values)
        info_parts = [semantic["project_fit"], semantic["decision_leverage"], semantic["information_uncertainty"]]
        information_gain = 100.0 * (math.prod(info_parts) ** (1.0 / 3.0) if all(info_parts) else 0.0)
        strategic = weighted_sum(recommended_weights, {
            "science": science,
            "information_gain": information_gain,
            "feasibility": feasibility,
        })
        cost_norm = parse_int(str(semantic_row.get("estimated_reading_cost", "3")), 3) / 5.0
        fast_roi = science * (
            float(roi_cfg.get("feasibility_floor", 0.55))
            + float(roi_cfg.get("feasibility_span", 0.45)) * feasibility / 100.0
        ) / (
            float(roi_cfg.get("cost_floor", 0.65))
            + float(roi_cfg.get("cost_span", 0.35)) * cost_norm
        )
        fast_roi = max(0.0, min(100.0, fast_roi))
        base_priority = weighted_sum(base_weights, {"strategic": strategic, "fast_roi": fast_roi})
        row = {
            **candidate,
            **{key: semantic_row.get(key, "") for key in SCORE_FIELDS if key not in candidate},
            "semantic_score_source": source,
            "norm_network_breadth": round(normalized["network_breadth"][index], 6),
            "norm_citation_velocity": round(normalized["citation_velocity"][index], 6),
            "norm_recency": round(normalized["recency"][index], 6),
            "science_score": round(science, 6),
            "feasibility_score": round(feasibility, 6),
            "information_gain_score": round(information_gain, 6),
            "strategic_score": round(strategic, 6),
            "fast_roi_score": round(fast_roi, 6),
            "base_priority_score": round(base_priority, 6),
        }
        row["_tags"] = tag_set(row)
        rows.append(row)

    science_rank = rank_positions(rows, "science_score")
    roi_rank = rank_positions(rows, "fast_roi_score")
    info_rank = rank_positions(rows, "information_gain_score")
    base_rank = rank_positions(rows, "base_priority_score")
    sensitivity = sensitivity_analysis(rows, config) if with_sensitivity else {}
    pareto = pareto_layers(rows)
    reranked = diversity_rerank(rows, config)
    recommended_rank = {row["candidate_id"]: position for position, row in enumerate(reranked, start=1)}
    tier_a = int(config["tiers"].get("tier_a_count", 40))
    tier_b = int(config["tiers"].get("tier_b_count", 80))
    pinned = set(config.get("policy", {}).get("pinned_candidate_ids", []))

    for row in rows:
        cid = row["candidate_id"]
        row["scientific_priority_rank"] = science_rank[cid]
        row["fast_roi_rank"] = roi_rank[cid]
        row["information_gain_rank"] = info_rank[cid]
        row["base_priority_rank"] = base_rank[cid]
        row["recommended_fulltext_rank"] = recommended_rank[cid]
        row["pareto_layer"] = pareto[cid]
        row["pareto_front"] = "yes" if pareto[cid] == 1 else "no"
        if sensitivity:
            row.update(sensitivity[cid])
        else:
            row.update({
                "sensitivity_mean_rank": "", "sensitivity_median_rank": "",
                "sensitivity_rank_sd": "", "sensitivity_p_top20": "",
                "sensitivity_p_top40": "", "sensitivity_p_top80": "",
                "rank_stability": "not_run",
            })
        if cid in pinned:
            tier = "A0_anchor"
        elif recommended_rank[cid] <= tier_a:
            tier = "A_decision_critical"
        elif recommended_rank[cid] <= tier_a + tier_b:
            tier = "B_high_roi"
        else:
            tier = "C_supporting"
        row["priority_tier"] = tier
        row["diversity_tags"] = ";".join(sorted(row.pop("_tags")))
    ordered = sorted(rows, key=lambda row: int(row["recommended_fulltext_rank"]))
    return ordered, candidates, decisions_path, queue_path


def write_ranking_run(repo: Path, config: dict[str, Any], mode: str) -> dict[str, Any]:
    ordered, candidates, decisions_path, queue_path = build_rank_rows(repo, config, mode=mode, with_sensitivity=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "BOOTSTRAP" if mode == "bootstrap" else "RANK"
    parent = "bootstrap_runs" if mode == "bootstrap" else "runs"
    run_id = f"{prefix}_{timestamp}"
    run_dir = repo / "outputs/fulltext_ranking" / parent / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    fields = list(ordered[0].keys()) if ordered else []
    write_csv(run_dir / "recommended_fulltext_queue.csv", ordered, fields)
    write_csv(run_dir / "science_priority.csv", sorted(ordered, key=lambda row: int(row["scientific_priority_rank"])), fields)
    write_csv(run_dir / "fast_roi_priority.csv", sorted(ordered, key=lambda row: int(row["fast_roi_rank"])), fields)
    write_csv(run_dir / "information_gain_priority.csv", sorted(ordered, key=lambda row: int(row["information_gain_rank"])), fields)
    write_csv(run_dir / "next_20_fulltext.csv", ordered[:20], fields)
    unscored = [row for row in ordered if row.get("semantic_score_source") != "ai"]
    write_csv(run_dir / "next_20_ai_scoring.csv", unscored[:20], fields)
    write_csv(run_dir / "bootstrap_fallback_candidates.csv", unscored, fields)

    score_history = repo / "data/curated/ranking/paper_priority_score_history.csv"
    manifest = {
        "run_id": run_id,
        "mode": mode,
        "created_at": utc_now(),
        "protocol_version": config["project"].get("protocol_version", PROTOCOL),
        "included_papers": len(candidates),
        "ai_scored_papers": sum(row.get("semantic_score_source") == "ai" for row in ordered),
        "bootstrap_fallback_papers": len(unscored),
        "source_decisions": str(decisions_path.relative_to(repo)).replace("\\", "/"),
        "source_decisions_sha256": sha256_file(decisions_path),
        "source_queue": str(queue_path.relative_to(repo)).replace("\\", "/"),
        "source_queue_sha256": sha256_file(queue_path),
        "score_history": str(score_history.relative_to(repo)).replace("\\", "/"),
        "score_history_sha256": sha256_file(score_history) if score_history.exists() else None,
        "config": "config/fulltext_ranking.toml",
        "config_sha256": sha256_file(repo / "config/fulltext_ranking.toml"),
        "weights": config["weights"],
        "roi": config["roi"],
        "diversity": config["diversity"],
        "sensitivity": config.get("sensitivity", {}),
        "tiers": config["tiers"],
        "interpretation": "Sensitivity frequencies are policy-weight stability scenarios, not calibrated probabilities of scientific truth.",
    }
    (run_dir / "ranking_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    top20 = ordered[:20]
    theme_counts = Counter(str(row.get("primary_theme", "unknown")) for row in top20)
    dataset_counts = Counter(str(row.get("dataset_cluster", "unknown")) for row in top20)
    stability_counts = Counter(str(row.get("rank_stability", "unknown")) for row in ordered)
    report = [
        "# Full-text evidence-priority ranking", "",
        f"- Run: `{run_id}`", f"- Mode: `{mode}`", f"- Included papers: {len(candidates)}",
        f"- AI semantic scores: {manifest['ai_scored_papers']}",
        f"- Bootstrap fallback scores: {manifest['bootstrap_fallback_papers']}",
        f"- Protocol: `{manifest['protocol_version']}`", "",
        "## Rank stability", "",
    ]
    report.extend(f"- {key}: {value}" for key, value in stability_counts.items())
    report.extend(["", "## Top-20 theme coverage", ""])
    report.extend(f"- {key}: {value}" for key, value in theme_counts.most_common())
    report.extend(["", "## Top-20 dataset-cluster coverage", ""])
    report.extend(f"- {key}: {value}" for key, value in dataset_counts.most_common())
    report.extend(["", "## Top-20 recommended papers", ""])
    for row in top20:
        report.append(
            f"{row['recommended_fulltext_rank']}. **{row['title']}** — science {float(row['science_score']):.1f}, "
            f"ROI {float(row['fast_roi_score']):.1f}, information gain {float(row['information_gain_score']):.1f}; "
            f"source `{row['semantic_score_source']}`, stability `{row['rank_stability']}`."
        )
    report.extend([
        "", "This queue orders work; it does not exclude any title/abstract inclusion.",
        "Sensitivity frequencies describe stability under plausible scoring/weight perturbations, not posterior probabilities.",
    ])
    (run_dir / "ranking_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    pointer_name = "latest_bootstrap.json" if mode == "bootstrap" else "latest_ranking.json"
    pointer = {
        "run_id": run_id,
        "run_dir": str(run_dir.relative_to(repo)).replace("\\", "/"),
        "created_at": manifest["created_at"],
        "mode": mode,
    }
    (repo / "outputs/fulltext_ranking" / pointer_name).parent.mkdir(parents=True, exist_ok=True)
    (repo / "outputs/fulltext_ranking" / pointer_name).write_text(json.dumps(pointer, indent=2), encoding="utf-8")
    return {**pointer, **{k: manifest[k] for k in ("included_papers", "ai_scored_papers", "bootstrap_fallback_papers")}}


def bootstrap(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    result = write_ranking_run(repo, load_config(repo, args.config), mode="bootstrap")
    print(json.dumps(result, indent=2))
    return 0


def build(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    result = write_ranking_run(repo, load_config(repo, args.config), mode="hybrid")
    print(json.dumps(result, indent=2))
    return 0


def latest_queue_for_scoring(repo: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], str, str]:
    pointer = repo / "outputs/fulltext_ranking/latest_ranking.json"
    if pointer.exists():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        path = repo / data["run_dir"] / "recommended_fulltext_queue.csv"
        if path.exists():
            return read_csv(path), str(path.relative_to(repo)).replace("\\", "/"), sha256_file(path)
    pointer = repo / "outputs/fulltext_ranking/latest_bootstrap.json"
    if pointer.exists():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        path = repo / data["run_dir"] / "recommended_fulltext_queue.csv"
        if path.exists():
            return read_csv(path), str(path.relative_to(repo)).replace("\\", "/"), sha256_file(path)
    ordered, _, _, _ = build_rank_rows(repo, config, mode="hybrid", with_sensitivity=False)
    return ordered, "generated_in_memory", ""


def prepare(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    config = load_config(repo, args.config)
    candidates, decisions_path, queue_path = build_candidates(repo, config)
    candidate_by_id = {row["candidate_id"]: row for row in candidates}
    scored = {row.get("candidate_id", "") for row in active_scores(repo)}
    priority_rows, source_ranking_path, source_ranking_sha = latest_queue_for_scoring(repo, config)
    unscored_priority = [row for row in priority_rows if row.get("candidate_id") not in scored]
    if not unscored_priority:
        print(json.dumps({"status": "complete", "included": len(candidates), "unscored": 0}, indent=2))
        return 0
    start, end = parse_range(args.range, len(unscored_priority))
    selected_rank_rows = unscored_priority[start - 1:end]
    selected: list[dict[str, Any]] = []
    for position, ranked in enumerate(selected_rank_rows, start=start):
        candidate = dict(candidate_by_id[ranked["candidate_id"]])
        candidate["unscored_priority_position"] = position
        candidate["current_recommended_fulltext_rank"] = ranked.get("recommended_fulltext_rank", "")
        candidate["bootstrap_project_fit"] = ranked.get("project_fit", "")
        candidate["bootstrap_dataset_evidence_value"] = ranked.get("dataset_evidence_value", "")
        candidate["bootstrap_method_gap_value"] = ranked.get("method_gap_value", "")
        candidate["bootstrap_information_uncertainty"] = ranked.get("information_uncertainty", "")
        selected.append(candidate)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_id = f"RB_{start:04d}_{end:04d}_{timestamp}"
    batch_dir = repo / "outputs/fulltext_ranking/scoring_batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)
    input_path = batch_dir / "input_rows.csv"
    write_csv(input_path, selected)
    template_rows: list[dict[str, Any]] = []
    for row in selected:
        template_rows.append({
            "score_id": f"PR_{short_hash(row['candidate_id'] + '|' + batch_id, 16)}",
            "candidate_id": row["candidate_id"],
            "included_order": row["included_order"],
            "original_screening_rank": row["original_screening_rank"],
            "title": row["title"],
            "project_fit": "", "dataset_evidence_value": "", "method_gap_value": "",
            "decision_leverage": "", "actual_use_likelihood": "", "evidence_specificity": "",
            "information_uncertainty": "", "estimated_reading_cost": "", "primary_role": "",
            "primary_theme": "", "dataset_cluster": "", "task_cluster": "",
            "modality_cluster": "", "score_confidence": "", "evidence_note": "",
            "reviewer": "opencode_ai", "model": "", "protocol_version": PROTOCOL,
            "scored_at": "", "supersedes_score_id": "", "notes": "",
        })
    template_path = batch_dir / "scored_rows_template.csv"
    write_csv(template_path, template_rows, SCORE_FIELDS)
    manifest = {
        "batch_id": batch_id,
        "created_at": utc_now(),
        "priority_position_start": start,
        "priority_position_end": end,
        "candidate_count": len(selected),
        "input_rows": str(input_path.relative_to(repo)).replace("\\", "/"),
        "input_rows_sha256": sha256_file(input_path),
        "template_rows": str(template_path.relative_to(repo)).replace("\\", "/"),
        "template_rows_sha256": sha256_file(template_path),
        "source_decisions": str(decisions_path.relative_to(repo)).replace("\\", "/"),
        "source_decisions_sha256": sha256_file(decisions_path),
        "source_queue": str(queue_path.relative_to(repo)).replace("\\", "/"),
        "source_queue_sha256": sha256_file(queue_path),
        "source_ranking": source_ranking_path,
        "source_ranking_sha256": source_ranking_sha,
        "protocol_version": config["project"].get("protocol_version", PROTOCOL),
    }
    (batch_dir / "batch_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = [
        "# Priority-scoring batch", "", f"- Batch: `{batch_id}`",
        f"- Unscored priority positions: {start}-{end}", f"- Papers: {len(selected)}",
        f"- Source ranking: `{source_ranking_path}`", "",
        "Fill `scored_rows.csv` from the template. Do not change identity fields.",
        "Bootstrap columns in `input_rows.csv` are scheduling hints, not answers; apply the skill rubric independently.",
    ]
    (batch_dir / "batch_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({
        "batch_id": batch_id,
        "batch_dir": str(batch_dir.relative_to(repo)).replace("\\", "/"),
        "candidate_count": len(selected),
        "remaining_unscored_after_batch": len(unscored_priority) - len(selected),
    }, indent=2))
    return 0


def validate_score_row(row: dict[str, str], expected: dict[str, str], active_by_candidate: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for field in ("candidate_id", "included_order", "original_screening_rank", "title"):
        if str(row.get(field, "")) != str(expected.get(field, "")):
            errors.append(f"{field} changed")
    for field in (
        "project_fit", "dataset_evidence_value", "method_gap_value", "decision_leverage",
        "actual_use_likelihood", "evidence_specificity", "information_uncertainty",
    ):
        value = row.get(field, "")
        if not re.fullmatch(r"[0-4]", value or ""):
            errors.append(f"{field} must be integer 0-4")
    if not re.fullmatch(r"[1-5]", row.get("estimated_reading_cost", "") or ""):
        errors.append("estimated_reading_cost must be integer 1-5")
    if row.get("primary_role") not in ROLES:
        errors.append("invalid primary_role")
    if row.get("primary_theme") not in THEMES:
        errors.append("invalid primary_theme")
    if row.get("score_confidence") not in CONFIDENCE:
        errors.append("invalid score_confidence")
    if not row.get("evidence_note", "").strip():
        errors.append("evidence_note required")
    if not row.get("reviewer", "").strip() or not row.get("model", "").strip():
        errors.append("reviewer and model required")
    if row.get("protocol_version") != PROTOCOL:
        errors.append(f"protocol_version must be {PROTOCOL}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", row.get("scored_at", "") or ""):
        errors.append("scored_at must be UTC ISO timestamp")
    active = active_by_candidate.get(row.get("candidate_id", ""))
    if active:
        if row.get("supersedes_score_id") != active.get("score_id"):
            errors.append(f"existing active score must be superseded by ID {active.get('score_id')}")
    elif row.get("supersedes_score_id", "").strip():
        errors.append("supersedes_score_id set but no active score exists")
    return errors


def latest_pending_batch(repo: Path) -> Path:
    root = repo / "outputs/fulltext_ranking/scoring_batches"
    pending = [path for path in root.glob("RB_*") if (path / "batch_manifest.json").exists() and not (path / "finalized.json").exists()]
    if not pending:
        raise FileNotFoundError("No pending priority-scoring batch found")
    return sorted(pending)[-1]


def finalize_batch(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    batch_dir = Path(args.batch) if args.batch else latest_pending_batch(repo)
    if not batch_dir.is_absolute():
        batch_dir = repo / batch_dir
    manifest_path = batch_dir / "batch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("protocol_version") != PROTOCOL:
        raise ValueError("Batch protocol does not match current protocol")
    if sha256_file(repo / manifest["source_decisions"]) != manifest["source_decisions_sha256"]:
        raise ValueError("Source decision snapshot changed after batch preparation")
    if sha256_file(repo / manifest["source_queue"]) != manifest["source_queue_sha256"]:
        raise ValueError("Frozen queue changed after batch preparation")
    if manifest.get("source_ranking") not in {"", "generated_in_memory"}:
        ranking_path = repo / manifest["source_ranking"]
        if not ranking_path.exists() or sha256_file(ranking_path) != manifest.get("source_ranking_sha256", ""):
            raise ValueError("Source ranking changed after batch preparation")
    input_path = repo / manifest["input_rows"]
    if sha256_file(input_path) != manifest["input_rows_sha256"]:
        raise ValueError("Input rows changed after preparation")
    expected_rows = read_csv(input_path)
    scored_path = batch_dir / "scored_rows.csv"
    if not scored_path.exists():
        raise FileNotFoundError(f"Missing {scored_path}")
    scored = read_csv(scored_path)
    if len(scored) != len(expected_rows):
        raise ValueError(f"Expected {len(expected_rows)} scored rows, got {len(scored)}")
    expected = {row["candidate_id"]: row for row in expected_rows}
    active_by_candidate = {row.get("candidate_id", ""): row for row in active_scores(repo)}
    errors: list[str] = []
    seen_score_ids: set[str] = set()
    for row in scored:
        candidate_id = row.get("candidate_id", "")
        if candidate_id not in expected:
            errors.append(f"unknown candidate {candidate_id}")
            continue
        if row.get("score_id", "") in seen_score_ids:
            errors.append(f"duplicate score_id {row.get('score_id')}")
        seen_score_ids.add(row.get("score_id", ""))
        errors.extend(f"{candidate_id}: {message}" for message in validate_score_row(row, expected[candidate_id], active_by_candidate))
    validation_path = batch_dir / "validation_report.json"
    if errors:
        validation_path.write_text(json.dumps({"passed": False, "errors": errors}, indent=2), encoding="utf-8")
        raise ValueError(f"Priority score validation failed with {len(errors)} error(s)")
    history_path = repo / "data/curated/ranking/paper_priority_score_history.csv"
    append_csv(history_path, scored, SCORE_FIELDS)
    refresh_active_scores(repo)
    registry = repo / "data/curated/ranking/paper_priority_score_batches.csv"
    registry_row = {
        "batch_id": manifest["batch_id"],
        "priority_position_start": manifest["priority_position_start"],
        "priority_position_end": manifest["priority_position_end"],
        "candidate_count": len(scored),
        "input_rows_path": manifest["input_rows"],
        "input_rows_sha256": manifest["input_rows_sha256"],
        "scored_rows_path": str(scored_path.relative_to(repo)).replace("\\", "/"),
        "scored_rows_sha256": sha256_file(scored_path),
        "source_decisions_path": manifest["source_decisions"],
        "source_decisions_sha256": manifest["source_decisions_sha256"],
        "source_queue_path": manifest["source_queue"],
        "source_queue_sha256": manifest["source_queue_sha256"],
        "source_ranking_path": manifest.get("source_ranking", ""),
        "source_ranking_sha256": manifest.get("source_ranking_sha256", ""),
        "protocol_version": manifest["protocol_version"],
        "reviewer": ";".join(sorted({row["reviewer"] for row in scored})),
        "model": ";".join(sorted({row["model"] for row in scored})),
        "completed_at": utc_now(),
        "validation_status": "passed",
        "notes": "",
    }
    append_csv(registry, [registry_row], BATCH_FIELDS)
    validation_path.write_text(json.dumps({"passed": True, "rows": len(scored)}, indent=2), encoding="utf-8")
    finalized = {
        "batch_id": manifest["batch_id"], "finalized_at": utc_now(), "rows": len(scored),
        "scored_rows_sha256": sha256_file(scored_path),
    }
    (batch_dir / "finalized.json").write_text(json.dumps(finalized, indent=2), encoding="utf-8")
    print(json.dumps(finalized, indent=2))
    return 0


def latest_ranking_dir(repo: Path, supplied: str | None = None) -> Path:
    if supplied:
        path = Path(supplied)
        return path if path.is_absolute() else repo / path
    pointer = repo / "outputs/fulltext_ranking/latest_ranking.json"
    if pointer.exists():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        return repo / data["run_dir"]
    raise FileNotFoundError("No hybrid ranking run found. Run /rank-fulltext first.")


def latest_fulltext_decisions(repo: Path) -> dict[str, dict[str, str]]:
    path = repo / "data/curated/screening/full_text_decisions.csv"
    latest: dict[str, dict[str, str]] = {}
    for row in read_csv(path):
        paper_id = (row.get("paper_id") or row.get("candidate_id") or "").strip()
        if not paper_id:
            continue
        timestamp = row.get("reviewed_at") or row.get("reviewed_date") or row.get("decided_at") or ""
        event_id = row.get("fulltext_screening_id") or row.get("decision_id") or ""
        previous = latest.get(paper_id)
        if previous is None:
            latest[paper_id] = row
            continue
        previous_timestamp = previous.get("reviewed_at") or previous.get("reviewed_date") or previous.get("decided_at") or ""
        previous_id = previous.get("fulltext_screening_id") or previous.get("decision_id") or ""
        if (timestamp, event_id) >= (previous_timestamp, previous_id):
            latest[paper_id] = row
    return latest


def graded_relevance(decision: str) -> int:
    return {"include_core": 3, "include_supporting": 1, "exclude": 0, "unresolved": 0}.get(decision, 0)


def dcg(values: Sequence[int]) -> float:
    return sum((2 ** value - 1) / math.log2(index + 2) for index, value in enumerate(values))


def ordering_metrics(rows: list[dict[str, str]], outcomes: dict[str, dict[str, str]], k: int) -> dict[str, Any]:
    subset = rows[:k]
    known = [row for row in subset if row.get("candidate_id") in outcomes]
    all_known_core = sum(1 for value in outcomes.values() if value.get("decision") == "include_core")
    values = [graded_relevance(outcomes[row["candidate_id"]].get("decision", "")) for row in known]
    core = sum(1 for row in known if outcomes[row["candidate_id"]].get("decision") == "include_core")
    ideal = sorted(values, reverse=True)
    return {
        "known": len(known),
        "core_precision": core / len(known) if known else None,
        "core_recall": core / all_known_core if all_known_core else None,
        "graded_ndcg": dcg(values) / dcg(ideal) if ideal and dcg(ideal) else None,
        "cumulative_gain": sum(values),
        "unique_dataset_clusters": len({row.get("dataset_cluster", "unknown") for row in known}),
        "unique_themes": len({row.get("primary_theme", "unknown") for row in known}),
    }


def evaluate(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    config = load_config(repo, args.config)
    run_dir = latest_ranking_dir(repo, args.run)
    queue = read_csv(run_dir / "recommended_fulltext_queue.csv")
    outcomes = latest_fulltext_decisions(repo)
    if not outcomes:
        raise ValueError("No full-text decision outcomes are available")
    orderings: dict[str, list[dict[str, str]]] = {
        "recommended": queue,
        "science": sorted(queue, key=lambda row: parse_int(row.get("scientific_priority_rank", ""), 10**9)),
        "fast_roi": sorted(queue, key=lambda row: parse_int(row.get("fast_roi_rank", ""), 10**9)),
        "information_gain": sorted(queue, key=lambda row: parse_int(row.get("information_gain_rank", ""), 10**9)),
        "original_screening": sorted(queue, key=lambda row: parse_int(row.get("original_screening_rank", ""), 10**9)),
    }
    metrics: dict[str, Any] = {
        "ranking_run": str(run_dir.relative_to(repo)).replace("\\", "/"),
        "evaluated_at": utc_now(),
        "ranked_papers": len(queue),
        "fulltext_outcomes": len(outcomes),
        "minimum_outcomes_for_recalibration": int(config["policy"].get("minimum_outcomes_for_recalibration", 40)),
        "recalibration_ready": len(outcomes) >= int(config["policy"].get("minimum_outcomes_for_recalibration", 40)),
        "orderings": {},
    }
    for name, rows in orderings.items():
        ordering_result: dict[str, Any] = {}
        for k in (20, 40, 80):
            ordering_result[f"at_{k}"] = ordering_metrics(rows, outcomes, k)
        core_positions = [
            index for index, row in enumerate(rows, start=1)
            if row.get("candidate_id") in outcomes and outcomes[row["candidate_id"]].get("decision") == "include_core"
        ]
        ordering_result["papers_to_first_core"] = min(core_positions) if core_positions else None
        ordering_result["mean_core_discovery_rank"] = statistics.fmean(core_positions) if core_positions else None
        ordering_result["normalized_average_time_to_core"] = (
            statistics.fmean(core_positions) / len(rows) if core_positions and rows else None
        )
        metrics["orderings"][name] = ordering_result
    output_dir = run_dir / "evaluation"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "ranking_evaluation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    lines = ["# Ranking evaluation", "", f"- Outcomes: {len(outcomes)}", f"- Recalibration ready: {metrics['recalibration_ready']}", ""]
    for name, values in metrics["orderings"].items():
        lines.extend([f"## {name}", ""])
        lines.append(f"- Papers to first core: {values['papers_to_first_core']}")
        lines.append(f"- Normalized average time to core: {values['normalized_average_time_to_core']}")
        for k in (20, 40, 80):
            current = values[f"at_{k}"]
            lines.append(
                f"- @{k}: known={current['known']}, core precision={current['core_precision']}, "
                f"core recall={current['core_recall']}, NDCG={current['graded_ndcg']}, gain={current['cumulative_gain']}"
            )
        lines.append("")
    lines.extend(["Weights were not changed automatically.", "Preserve the v1 run before any protocol revision."])
    (output_dir / "ranking_evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


def status(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    config = load_config(repo, args.config)
    candidates, _, _ = build_candidates(repo, config)
    scores = active_scores(repo)
    history = read_csv(repo / "data/curated/ranking/paper_priority_score_history.csv")
    outcomes = latest_fulltext_decisions(repo)
    latest_rank = repo / "outputs/fulltext_ranking/latest_ranking.json"
    latest_bootstrap = repo / "outputs/fulltext_ranking/latest_bootstrap.json"
    result = {
        "included_papers": len(candidates),
        "active_ai_priority_scores": len(scores),
        "bootstrap_fallback_papers": max(0, len(candidates) - len(scores)),
        "priority_score_history_events": len(history),
        "fulltext_outcomes": len(outcomes),
        "latest_hybrid_ranking": json.loads(latest_rank.read_text(encoding="utf-8")) if latest_rank.exists() else None,
        "latest_bootstrap_ranking": json.loads(latest_bootstrap.read_text(encoding="utf-8")) if latest_bootstrap.exists() else None,
        "next_command": "/bootstrap-ranking" if not latest_bootstrap.exists() else ("/prepare-priority" if len(scores) < len(candidates) else "/rank-fulltext"),
    }
    print(json.dumps(result, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--repo", default=".")
    root.add_argument("--config", default=None)
    sub = root.add_subparsers(dest="command", required=True)
    p_bootstrap = sub.add_parser("bootstrap")
    p_bootstrap.set_defaults(func=bootstrap)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--range", default=None)
    p_prepare.set_defaults(func=prepare)
    p_finalize = sub.add_parser("finalize-batch")
    p_finalize.add_argument("--batch", default=None)
    p_finalize.set_defaults(func=finalize_batch)
    p_build = sub.add_parser("build")
    p_build.set_defaults(func=build)
    p_status = sub.add_parser("status")
    p_status.set_defaults(func=status)
    p_eval = sub.add_parser("evaluate")
    p_eval.add_argument("--run", default=None)
    p_eval.set_defaults(func=evaluate)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
