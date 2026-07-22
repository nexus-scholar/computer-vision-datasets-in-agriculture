#!/usr/bin/env python3
"""Build a provenance-preserving graph from human-accepted seed/provider identities.

Run directories are supplied oldest to newest. For each accepted seed/provider pair,
the newest run whose resolved identity matches the human audit row is selected. Pairs
with missing identity evidence or incomplete relations are omitted by default and
reported explicitly.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ACCEPTED_STATUSES = {"accepted", "accepted_with_note"}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    seed_row_id: str
    provider: str
    message: str
    evidence: str = ""
    recommended_action: str = ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean_doi(value: str) -> str:
    value = (value or "").strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value.rstrip("./")


def normalize_id(provider: str, value: str) -> str:
    value = (value or "").strip()
    if provider == "openalex":
        value = re.sub(r"^https?://openalex\.org/", "", value, flags=re.I)
    return value.casefold()


def to_int(value: str) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def identity_matches(audit: dict[str, str], provider_row: dict[str, str]) -> tuple[bool, str]:
    provider = audit.get("provider", "").strip().casefold()
    candidate_id = normalize_id(provider, audit.get("candidate_id", ""))
    provider_id = normalize_id(provider, provider_row.get("provider_work_id", ""))
    if candidate_id:
        return candidate_id == provider_id, f"candidate_id={candidate_id}; provider_work_id={provider_id}"

    candidate_doi = clean_doi(audit.get("candidate_doi", ""))
    provider_doi = clean_doi(provider_row.get("doi", ""))
    if candidate_doi:
        return candidate_doi == provider_doi, f"candidate_doi={candidate_doi}; provider_doi={provider_doi}"

    return False, "Accepted row lacks candidate_id and candidate_doi; exact run identity cannot be verified."


def expected_downloaded(reported: int, cap: int) -> int:
    return min(reported, cap) if cap > 0 else reported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a graph from human-accepted seed/provider identities.")
    parser.add_argument("--runs", nargs="+", type=Path, required=True, help="Run directories, oldest to newest")
    parser.add_argument("--seed-audit", type=Path, required=True, help="Human-reviewed seed_resolution_audit.csv")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument(
        "--allow-incomplete-relations",
        action="store_true",
        help="Include accepted pairs whose downloaded relation counts are below the expected count",
    )
    parser.add_argument("--overwrite", action="store_true", help="Allow writing into an existing non-empty output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)

    run_dirs = [path.resolve() for path in args.runs]
    for run in run_dirs:
        if not (run / "seed_papers_provider_metadata.csv").exists():
            raise SystemExit(f"Missing seed provider metadata: {run}")
        if not (run / "snowball_edges.csv").exists():
            raise SystemExit(f"Missing snowball edges: {run}")

    audits = read_csv(args.seed_audit)
    accepted = [row for row in audits if row.get("identity_status", "").strip().casefold() in ACCEPTED_STATUSES]
    duplicate_audit_keys = [
        key for key, count in Counter(
            (row.get("seed_row_id", "").strip(), row.get("provider", "").strip().casefold())
            for row in accepted
        ).items() if count > 1
    ]
    if duplicate_audit_keys:
        raise SystemExit(f"Duplicate accepted seed/provider audit rows: {duplicate_audit_keys}")

    runs: list[dict[str, Any]] = []
    for order, run in enumerate(run_dirs):
        manifest_path = run / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        runs.append({
            "order": order,
            "path": run,
            "manifest": manifest,
            "provider_rows": read_csv(run / "seed_papers_provider_metadata.csv"),
            "summary_rows": read_csv(run / "run_summary.csv"),
            "edge_rows": read_csv(run / "snowball_edges.csv"),
        })

    issues: list[Issue] = []
    selections: list[dict[str, Any]] = []
    accepted_edges: list[dict[str, Any]] = []
    edge_fields: list[str] = []

    for audit in accepted:
        seed = audit.get("seed_row_id", "").strip()
        provider = audit.get("provider", "").strip().casefold()
        candidates: list[tuple[dict[str, Any], dict[str, str], str]] = []
        for run in runs:
            for provider_row in run["provider_rows"]:
                if provider_row.get("seed_row_id", "").strip() != seed:
                    continue
                if provider_row.get("provider", "").strip().casefold() != provider:
                    continue
                matches, evidence = identity_matches(audit, provider_row)
                if matches:
                    candidates.append((run, provider_row, evidence))
        if not candidates:
            issues.append(Issue(
                "critical", "accepted_identity_not_found", seed, provider,
                "No supplied run contains the exact provider identity accepted by the human audit.",
                f"candidate_id={audit.get('candidate_id','')}; candidate_doi={audit.get('candidate_doi','')}",
                "Repair or rerun this seed/provider pair; do not include its relations.",
            ))
            selections.append({
                "seed_row_id": seed, "provider": provider, "identity_status": audit.get("identity_status", ""),
                "selected_run": "", "selected_provider_work_id": "", "include_relations": "no",
                "exclusion_reason": "accepted_identity_not_found",
            })
            continue

        run, provider_row, identity_evidence = candidates[-1]
        summary = next((row for row in run["summary_rows"] if row.get("seed_row_id", "").strip() == seed and row.get("provider", "").strip().casefold() == provider), {})
        max_back = to_int(run["manifest"].get("max_backward_references", 0))
        max_forward = to_int(run["manifest"].get("max_forward_citations", 0))
        shortfalls: list[str] = []
        for direction, reported_field, downloaded_field, cap in (
            ("backward", "reported_reference_count", "downloaded_reference_rows", max_back),
            ("forward", "reported_citation_count", "downloaded_citation_rows", max_forward),
        ):
            reported = to_int(summary.get(reported_field, ""))
            downloaded = to_int(summary.get(downloaded_field, ""))
            expected = expected_downloaded(reported, cap)
            if downloaded < expected:
                shortfalls.append(f"{direction}: downloaded={downloaded}, expected={expected}, reported={reported}, cap={cap}")

        include = not shortfalls or args.allow_incomplete_relations
        if shortfalls:
            issues.append(Issue(
                "high", "relation_count_shortfall", seed, provider,
                "The selected accepted identity has incomplete downloaded citation relations.",
                "; ".join(shortfalls),
                "Rerun the relation fetch with credentials and inspect relation_errors.csv; include only with an explicit incomplete-data decision.",
            ))

        selected_id = provider_row.get("provider_work_id", "")
        pair_edges = [
            row for row in run["edge_rows"]
            if row.get("seed_row_id", "").strip() == seed
            and row.get("provider", "").strip().casefold() == provider
        ]
        bad_edge_ids = [
            row for row in pair_edges
            if row.get("seed_provider_work_id", "").strip()
            and normalize_id(provider, row.get("seed_provider_work_id", "")) != normalize_id(provider, selected_id)
        ]
        if bad_edge_ids:
            include = False
            issues.append(Issue(
                "critical", "edge_seed_identity_mismatch", seed, provider,
                "Relation rows do not consistently originate from the selected accepted provider work.",
                f"selected={selected_id}; mismatching_rows={len(bad_edge_ids)}",
                "Quarantine the pair and inspect the run-generation code or cache.",
            ))

        selections.append({
            "seed_row_id": seed,
            "dataset_name": audit.get("dataset_name", provider_row.get("dataset_name", "")),
            "provider": provider,
            "identity_status": audit.get("identity_status", ""),
            "selected_run": str(run["path"]),
            "selected_run_order": run["order"],
            "selected_provider_work_id": selected_id,
            "selected_doi": provider_row.get("doi", ""),
            "selected_title": provider_row.get("title", ""),
            "identity_evidence": identity_evidence,
            "relation_rows": len(pair_edges),
            "relation_complete": "no" if shortfalls else "yes",
            "include_relations": "yes" if include else "no",
            "exclusion_reason": "" if include else ("relation_count_shortfall" if shortfalls else "edge_seed_identity_mismatch"),
        })
        if include:
            for row in pair_edges:
                enriched = dict(row)
                enriched["source_run"] = str(run["path"])
                enriched["accepted_identity_status"] = audit.get("identity_status", "")
                accepted_edges.append(enriched)
                if not edge_fields:
                    edge_fields = list(row.keys()) + ["source_run", "accepted_identity_status"]

    selection_fields = [
        "seed_row_id", "dataset_name", "provider", "identity_status", "selected_run", "selected_run_order",
        "selected_provider_work_id", "selected_doi", "selected_title", "identity_evidence", "relation_rows",
        "relation_complete", "include_relations", "exclusion_reason",
    ]
    write_csv(out / "selected_seed_provider_runs.csv", selections, selection_fields)
    write_csv(out / "build_issues.csv", (asdict(issue) for issue in issues), [
        "severity", "code", "seed_row_id", "provider", "message", "evidence", "recommended_action",
    ])
    write_csv(out / "accepted_snowball_edges.csv", accepted_edges, edge_fields or [
        "seed_row_id", "provider", "direction", "related_title", "source_run", "accepted_identity_status",
    ])

    high_issues = [issue for issue in issues if issue.severity in {"critical", "high"}]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_runs_oldest_to_newest": [str(path) for path in run_dirs],
        "seed_audit": str(args.seed_audit.resolve()),
        "accepted_audit_pairs": len(accepted),
        "selected_pairs": sum(row.get("selected_run", "") != "" for row in selections),
        "included_pairs": sum(row.get("include_relations") == "yes" for row in selections),
        "omitted_pairs": sum(row.get("include_relations") != "yes" for row in selections),
        "accepted_edge_rows": len(accepted_edges),
        "allow_incomplete_relations": args.allow_incomplete_relations,
        "critical_or_high_issue_count": len(high_issues),
        "quality_gate_passed": not high_issues,
    }
    (out / "build_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    severity_counts = Counter(issue.severity for issue in issues)
    report = [
        "# Accepted graph build report", "",
        f"Generated: {manifest['created_utc']}", "",
        f"Quality gate passed: **{manifest['quality_gate_passed']}**", "",
        "## Counts", "",
        f"- Human-accepted seed/provider pairs: {manifest['accepted_audit_pairs']}",
        f"- Included pairs: {manifest['included_pairs']}",
        f"- Omitted pairs: {manifest['omitted_pairs']}",
        f"- Accepted relation rows: {manifest['accepted_edge_rows']}",
        f"- Critical/high issues: {manifest['critical_or_high_issue_count']}", "",
        "## Rule", "",
        "The newest supplied run is used only when its exact provider identity matches the human audit. Incomplete or identity-inconsistent pairs are omitted unless incomplete relations were explicitly allowed.", "",
        "## Issues", "",
        f"Critical: {severity_counts['critical']} · High: {severity_counts['high']} · Medium: {severity_counts['medium']} · Low: {severity_counts['low']}", "",
    ]
    for issue in issues:
        report.extend([
            f"### {issue.severity.upper()} — {issue.code} ({issue.seed_row_id}/{issue.provider})", "",
            issue.message, "", f"Evidence: {issue.evidence or 'n/a'}", "", f"Action: {issue.recommended_action}", "",
        ])
    (out / "build_report.md").write_text("\n".join(report), encoding="utf-8")

    print(f"Accepted graph output: {out}")
    print(f"Included pairs: {manifest['included_pairs']}; accepted edges: {len(accepted_edges)}")
    print(f"Quality gate passed: {manifest['quality_gate_passed']}")
    return 0 if manifest["quality_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
