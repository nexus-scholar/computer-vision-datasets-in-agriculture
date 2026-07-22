#!/usr/bin/env python3
"""Audit one OpenAlex/Semantic Scholar snowball run without changing it.

The script uses only the Python standard library. It turns silent data-quality
failures into explicit issues, metrics, and seed quarantine recommendations.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

REQUIRED_FILES = (
    "seed_papers_provider_metadata.csv",
    "run_summary.csv",
    "unresolved_seeds.csv",
    "snowball_edges.csv",
    "snowball_nodes.csv",
    "run_manifest.json",
)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    seed_row_id: str = ""
    provider: str = ""
    message: str = ""
    evidence: str = ""
    recommended_action: str = ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def normalize_text(value: str) -> str:
    value = (value or "").casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    containment = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
    return max(seq, 0.55 * jaccard + 0.45 * containment)


def clean_identifier(value: str) -> str:
    return (value or "").strip().casefold()


def canonical_related_key(row: dict[str, str]) -> str:
    doi = clean_identifier(row.get("related_doi", ""))
    if doi:
        doi = doi.removeprefix("https://doi.org/").removeprefix("doi:")
        return f"doi:{doi}"
    arxiv = clean_identifier(row.get("related_arxiv_id", ""))
    if arxiv:
        return f"arxiv:{arxiv.removeprefix('arxiv:')}"
    pmid = clean_identifier(row.get("related_pmid", ""))
    if pmid:
        return f"pmid:{pmid.removeprefix('pmid:')}"
    pmcid = clean_identifier(row.get("related_pmcid", ""))
    if pmcid:
        return f"pmcid:{pmcid.removeprefix('pmcid:')}"
    title = normalize_text(row.get("related_title", ""))
    year = (row.get("related_year", "") or "").strip()
    if title:
        return f"titleyear:{title}:{year}"
    # Provider-only IDs are preserved in raw provenance but are too weak for
    # cross-provider canonical screening when no title or stable identifier exists.
    return ""


def to_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def pct(n: int, d: int) -> str:
    return "0.0%" if d == 0 else f"{100.0*n/d:.1f}%"


def audit(run_dir: Path, min_title_score: float) -> tuple[list[Issue], dict[str, Any], set[str]]:
    issues: list[Issue] = []
    quarantine: set[str] = set()

    missing = [name for name in REQUIRED_FILES if not (run_dir / name).exists()]
    for name in missing:
        issues.append(Issue(
            "critical", "missing_required_file", message=f"Required run artifact is missing: {name}",
            evidence=str(run_dir / name), recommended_action="Regenerate or recover the file before using this run.",
        ))

    provider_rows = read_csv(run_dir / "seed_papers_provider_metadata.csv")
    summaries = read_csv(run_dir / "run_summary.csv")
    unresolved = read_csv(run_dir / "unresolved_seeds.csv")
    edges = read_csv(run_dir / "snowball_edges.csv")
    nodes = read_csv(run_dir / "snowball_nodes.csv")
    manifest = load_json(run_dir / "run_manifest.json")

    # Accepted seed identities must be exact-ID matches or strong title matches.
    for row in provider_rows:
        sid = row.get("seed_row_id", "")
        provider = row.get("provider", "")
        method = row.get("match_method", "")
        status = row.get("match_status", "")
        score = float(row.get("match_score") or 0.0)
        calculated = title_similarity(row.get("source_input_title", ""), row.get("title", ""))
        low = (
            "low_confidence" in method
            or "low_confidence" in status
            or (not method.startswith("identifier:") and score < min_title_score)
            or (not method.startswith("identifier:") and calculated < min_title_score)
        )
        if low:
            quarantine.add(sid)
            edge_count = sum(1 for edge in edges if edge.get("seed_row_id") == sid and edge.get("provider") == provider)
            issues.append(Issue(
                "critical", "accepted_low_confidence_seed", sid, provider,
                "A provider candidate was written as resolved even though its identity is below the acceptance threshold.",
                f"method={method}; stored_score={score:.4f}; recalculated_title_similarity={calculated:.4f}; edges={edge_count}; resolved_title={row.get('title','')}",
                "Quarantine this provider's seed metadata and all derived edges; repair the seed identity and rerun.",
            ))

    # Relation completeness. Respect explicit collection caps.
    max_back = to_int(manifest.get("max_backward_references")) or 0
    max_forward = to_int(manifest.get("max_forward_citations")) or 0
    for row in summaries:
        if row.get("status") != "resolved":
            continue
        sid, provider = row.get("seed_row_id", ""), row.get("provider", "")
        for relation, reported_col, downloaded_col, cap in (
            ("backward references", "reported_reference_count", "downloaded_reference_rows", max_back),
            ("forward citations", "reported_citation_count", "downloaded_citation_rows", max_forward),
        ):
            reported = to_int(row.get(reported_col))
            downloaded = to_int(row.get(downloaded_col))
            if reported is None or downloaded is None:
                continue
            expected = min(reported, cap) if cap else reported
            if downloaded < expected:
                ratio = downloaded / expected if expected else 1.0
                severity = "high" if downloaded == 0 or ratio < 0.8 else "medium"
                issues.append(Issue(
                    severity, "relation_shortfall", sid, provider,
                    f"Downloaded {relation} are below the provider-reported or configured expected count.",
                    f"reported={reported}; expected_after_cap={expected}; downloaded={downloaded}; completeness={ratio:.1%}",
                    "Refresh the provider relation endpoint with credentials and record any API error instead of treating it as zero relations.",
                ))

    for row in unresolved:
        issues.append(Issue(
            "medium", "unresolved_provider_seed", row.get("seed_row_id", ""), row.get("provider", ""),
            "The seed was not resolved by this provider.",
            f"reason={row.get('reason','')}; score={row.get('score','')}; cache={row.get('cache_path','')}",
            "Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.",
        ))

    if manifest:
        if not manifest.get("openalex_api_key_used", False):
            issues.append(Issue(
                "medium", "openalex_api_key_not_recorded", provider="openalex",
                message="The run manifest does not record use of an OpenAlex API key.",
                evidence=f"openalex_mailto_used={manifest.get('openalex_mailto_used', False)}; openalex_api_key_used={manifest.get('openalex_api_key_used', 'field absent')}",
                recommended_action="Use a current OpenAlex API key and record only a boolean, never the secret itself.",
            ))
        if not manifest.get("semantic_scholar_api_key_used", False):
            issues.append(Issue(
                "medium", "semantic_scholar_api_key_not_used", provider="semantic_scholar",
                message="The run was collected without a Semantic Scholar API key.",
                evidence="semantic_scholar_api_key_used=false",
                recommended_action="Use an API key for repair runs and preserve rate-limit/error diagnostics.",
            ))

    missing_title = [row for row in edges if not (row.get("related_title") or "").strip()]
    missing_id = [row for row in edges if not (row.get("related_provider_work_id") or "").strip()]
    if missing_title:
        issues.append(Issue(
            "medium", "edges_missing_related_title", message="Some relation rows have no related-paper title.",
            evidence=f"count={len(missing_title)} of {len(edges)} ({pct(len(missing_title), len(edges))})",
            recommended_action="Quarantine identity-empty rows or enrich them before canonical screening.",
        ))
    if missing_id:
        issues.append(Issue(
            "medium", "edges_missing_related_provider_id", message="Some relation rows have no provider work ID.",
            evidence=f"count={len(missing_id)} of {len(edges)} ({pct(len(missing_id), len(edges))})",
            recommended_action="Do not use these rows as stable graph nodes until another identifier is available.",
        ))

    exact_keys = Counter(
        tuple(row.get(col, "") for col in ("seed_row_id", "direction", "provider", "related_provider_work_id", "related_doi", "related_title", "related_year"))
        for row in edges
    )
    exact_duplicate_rows = sum(count - 1 for count in exact_keys.values() if count > 1)
    if exact_duplicate_rows:
        issues.append(Issue(
            "low", "exact_duplicate_edge_rows", message="The provider-level edge table contains exact duplicate relations.",
            evidence=f"redundant_rows={exact_duplicate_rows}",
            recommended_action="Retain raw rows for provenance but remove exact duplicates in the canonical corpus.",
        ))

    canonical_edge_keys: Counter[tuple[str, str, str]] = Counter()
    empty_identity_rows = 0
    canonical_identities: set[str] = set()
    for row in edges:
        key = canonical_related_key(row)
        if not key:
            empty_identity_rows += 1
            continue
        canonical_identities.add(key)
        canonical_edge_keys[(row.get("seed_row_id", ""), row.get("direction", ""), key)] += 1
    provider_duplicate_rows = sum(count - 1 for count in canonical_edge_keys.values() if count > 1)
    if provider_duplicate_rows:
        issues.append(Issue(
            "info", "cross_provider_duplicate_edges", message="The same canonical relation appears more than once across providers.",
            evidence=f"redundant_provider_rows={provider_duplicate_rows}; canonical_related_identities={len(canonical_identities)}",
            recommended_action="Screen a canonical table while preserving provider-level provenance separately.",
        ))
    if empty_identity_rows:
        issues.append(Issue(
            "high", "identity_empty_edges", message="Some edge rows cannot be assigned any canonical identity.",
            evidence=f"count={empty_identity_rows}",
            recommended_action="Quarantine these rows from screening and inspect raw provider responses.",
        ))

    title_year_groups: defaultdict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in nodes:
        title = normalize_text(row.get("title", ""))
        year = (row.get("year", "") or "").strip()
        if title:
            title_year_groups[(title, year)].append(row)
    duplicate_title_year_groups = sum(1 for group in title_year_groups.values() if len(group) > 1)
    if duplicate_title_year_groups:
        issues.append(Issue(
            "low", "duplicate_title_year_node_groups", message="Multiple node rows share the same normalized title and year.",
            evidence=f"groups={duplicate_title_year_groups}",
            recommended_action="Canonicalize by DOI/arXiv/PMID before title-year fallback and retain provider aliases.",
        ))

    metrics = {
        "audit_created_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "required_files_missing": len(missing),
        "seed_provider_rows": len(provider_rows),
        "seed_rows_merged_manifest": manifest.get("seed_count", ""),
        "unresolved_provider_rows": len(unresolved),
        "edge_rows": len(edges),
        "node_rows": len(nodes),
        "canonical_related_identities_approx": len(canonical_identities),
        "exact_duplicate_edge_rows": exact_duplicate_rows,
        "cross_provider_redundant_edge_rows": provider_duplicate_rows,
        "edges_missing_related_title": len(missing_title),
        "edges_missing_related_provider_id": len(missing_id),
        "identity_empty_edges": empty_identity_rows,
        "duplicate_title_year_node_groups": duplicate_title_year_groups,
        "quarantined_seed_ids": sorted(s for s in quarantine if s),
        "issue_counts": dict(Counter(issue.severity for issue in issues)),
        "quality_gate_passed": not any(issue.severity in {"critical", "high"} for issue in issues),
    }
    return sorted(issues, key=lambda issue: (SEVERITY_ORDER.get(issue.severity, 99), issue.seed_row_id, issue.code)), metrics, quarantine


def render_report(run_dir: Path, issues: list[Issue], metrics: dict[str, Any]) -> str:
    counts = Counter(issue.severity for issue in issues)
    lines = [
        f"# Snowball quality audit: `{run_dir.name}`",
        "",
        f"Generated: {metrics['audit_created_utc']}",
        "",
        "## Verdict",
        "",
    ]
    if metrics["quality_gate_passed"]:
        lines.append("**PASS with review notes.** No critical or high-severity issue was detected.")
    else:
        lines.append("**FAIL for synthesis.** Repair or quarantine all critical/high-severity issues before screening or making claims.")
    lines.extend([
        "",
        "## Core metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ])
    for key in (
        "seed_provider_rows", "unresolved_provider_rows", "edge_rows", "node_rows",
        "canonical_related_identities_approx", "cross_provider_redundant_edge_rows",
        "edges_missing_related_title", "edges_missing_related_provider_id",
        "duplicate_title_year_node_groups",
    ):
        lines.append(f"| `{key}` | {metrics.get(key, '')} |")
    lines.extend([
        "",
        f"Quarantined seed IDs: `{', '.join(metrics.get('quarantined_seed_ids', [])) or 'none'}`",
        "",
        "## Issues",
        "",
        f"Critical: {counts['critical']} · High: {counts['high']} · Medium: {counts['medium']} · Low: {counts['low']} · Info: {counts['info']}",
        "",
    ])
    if not issues:
        lines.append("No issues detected.")
    else:
        for issue in issues:
            scope = "/".join(part for part in (issue.seed_row_id, issue.provider) if part) or "run"
            lines.extend([
                f"### {issue.severity.upper()} — `{issue.code}` ({scope})",
                "",
                issue.message,
                "",
                f"**Evidence:** {issue.evidence or 'n/a'}",
                "",
                f"**Action:** {issue.recommended_action or 'Review manually.'}",
                "",
            ])
    lines.extend([
        "## Interpretation rule",
        "",
        "This audit evaluates generated provider metadata, not scientific relevance. Passing it means the graph is structurally usable; it does not mean a citing paper actually used a dataset. Actual use must be verified during full-text screening.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a generated OpenAlex/Semantic Scholar snowball run.")
    parser.add_argument("run_dir", type=Path, help="Run directory containing the snowball CSVs and manifest")
    parser.add_argument("--out", type=Path, help="Output audit directory (default: <run_dir>/quality_audit)")
    parser.add_argument("--min-title-score", type=float, default=0.88, help="Minimum accepted title-match score")
    parser.add_argument("--strict", action="store_true", help="Exit 2 for critical/high issues and 1 for warnings")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    out_dir = (args.out or (run_dir / "quality_audit")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    issues, metrics, quarantine = audit(run_dir, args.min_title_score)
    write_csv(out_dir / "issues.csv", (asdict(issue) for issue in issues), [
        "severity", "code", "seed_row_id", "provider", "message", "evidence", "recommended_action",
    ])
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "quarantine_seed_ids.txt").write_text("\n".join(sorted(quarantine)) + ("\n" if quarantine else ""), encoding="utf-8")
    (out_dir / "audit_report.md").write_text(render_report(run_dir, issues, metrics), encoding="utf-8")

    print(f"Audit written to: {out_dir}")
    print(f"Quality gate passed: {metrics['quality_gate_passed']}")
    print(f"Quarantined seeds: {', '.join(sorted(quarantine)) or 'none'}")

    if args.strict:
        severities = {issue.severity for issue in issues}
        if severities & {"critical", "high"}:
            return 2
        if severities & {"medium", "low"}:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
