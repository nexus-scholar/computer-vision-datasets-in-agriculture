# Snowball quality audit: `snowball_repair_2026-07-22`

Generated: 2026-07-22T14:32:33.963106+00:00

## Verdict

**FAIL for synthesis.** Repair or quarantine all critical/high-severity issues before screening or making claims.

## Core metrics

| Metric | Value |
|---|---:|
| `seed_provider_rows` | 7 |
| `unresolved_provider_rows` | 7 |
| `edge_rows` | 266 |
| `node_rows` | 251 |
| `canonical_related_identities_approx` | 244 |
| `cross_provider_redundant_edge_rows` | 0 |
| `edges_missing_related_title` | 16 |
| `edges_missing_related_provider_id` | 0 |
| `duplicate_title_year_node_groups` | 1 |

Quarantined seed IDs: `none`

## Issues

Critical: 0 · High: 1 · Medium: 8 · Low: 1 · Info: 0

### HIGH — `identity_empty_edges` (run)

Some edge rows cannot be assigned any canonical identity.

**Evidence:** count=16

**Action:** Quarantine these rows from screening and inspect raw provider responses.

### MEDIUM — `edges_missing_related_title` (run)

Some relation rows have no related-paper title.

**Evidence:** count=16 of 266 (6.0%)

**Action:** Quarantine identity-empty rows or enrich them before canonical screening.

### MEDIUM — `unresolved_provider_seed` (P001/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\b63f06b66d8260a14d49a73be85f9351b523c17e2b8c775fa474eb45cb5428a0.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P003/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\0114edc4f9fff435a3293bd22cdf9cd874e59a350d2a16837a6de6e6e57355d7.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P004/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\e415073f63534fd03ab3e4c44829891e3c0627a0a47355f76812bd3e27d02295.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P005/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\f2204efbf8ab2a1ff9909fcbbadcff17ceb212f0521725172277ee061c2c0a6b.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P007/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\02fa856860213602c344c7d7c9d6b59a5d5b06c96b6d259620586b8cc56c305e.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P012/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\94b4d600c2c5b021cc24828eb338d5a3e18ac3d697dbf218ca09b93097785dce.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P013/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_repair_2026-07-22\cache\529547f4a0f0755ffe6fcbcc543393f60d8b33d0bb6ef6362064ca50df617d64.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### LOW — `duplicate_title_year_node_groups` (run)

Multiple node rows share the same normalized title and year.

**Evidence:** groups=1

**Action:** Canonicalize by DOI/arXiv/PMID before title-year fallback and retain provider aliases.

## Interpretation rule

This audit evaluates generated provider metadata, not scientific relevance. Passing it means the graph is structurally usable; it does not mean a citing paper actually used a dataset. Actual use must be verified during full-text screening.
