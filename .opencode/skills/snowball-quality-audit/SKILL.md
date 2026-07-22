---
name: snowball-quality-audit
description: Audit a snowball run for accepted low-confidence seeds, unresolved providers, relation shortfalls, duplicate edges/nodes, empty identities, provider conflicts, and missing provenance.
compatibility: opencode
metadata:
  project: agri-cv
  risk: critical
---

## Required checks

- Required files and manifest exist.
- Every snowballed seed is accepted.
- Downloaded relation counts match provider-reported counts or have an explained cap.
- Provider errors are visible, not silently converted to zero.
- No edges originate from quarantined seeds.
- Canonical deduplication uses DOI, arXiv, PMID/PMCID, then normalized title-year.
- Provider-specific IDs and counts are retained as provenance.
- Empty-title/empty-ID rows are quarantined.
- Run credentials, limits, timestamps, input paths, and hashes are recorded.

Output critical issues, warnings, metrics, quarantine seed IDs, and a pass/fail decision.
