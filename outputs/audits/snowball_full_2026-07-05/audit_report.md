# Snowball quality audit: `snowball_full_2026-07-05`

Generated: 2026-07-22T14:25:50.654915+00:00

## Verdict

**FAIL for synthesis.** Repair or quarantine all critical/high-severity issues before screening or making claims.

## Core metrics

| Metric | Value |
|---|---:|
| `seed_provider_rows` | 19 |
| `unresolved_provider_rows` | 7 |
| `edge_rows` | 918 |
| `node_rows` | 689 |
| `canonical_related_identities_approx` | 677 |
| `cross_provider_redundant_edge_rows` | 154 |
| `edges_missing_related_title` | 41 |
| `edges_missing_related_provider_id` | 35 |
| `duplicate_title_year_node_groups` | 8 |

Quarantined seed IDs: `P004`

## Issues

Critical: 1 · High: 2 · Medium: 11 · Low: 1 · Info: 1

### CRITICAL — `accepted_low_confidence_seed` (P004/openalex)

A provider candidate was written as resolved even though its identity is below the acceptance threshold.

**Evidence:** method=low_confidence_search_title; stored_score=0.3814; recalculated_title_similarity=0.3814; edges=241; resolved_title=Intelligent Fruit Yield Estimation for Orchards Using Deep Learning Based Semantic Segmentation Techniques—A Review

**Action:** Quarantine this provider's seed metadata and all derived edges; repair the seed identity and rerun.

### HIGH — `identity_empty_edges` (run)

Some edge rows cannot be assigned any canonical identity.

**Evidence:** count=41

**Action:** Quarantine these rows from screening and inspect raw provider responses.

### HIGH — `relation_shortfall` (P007/semantic_scholar)

Downloaded backward references are below the provider-reported or configured expected count.

**Evidence:** reported=65; expected_after_cap=65; downloaded=0; completeness=0.0%

**Action:** Refresh the provider relation endpoint with credentials and record any API error instead of treating it as zero relations.

### MEDIUM — `edges_missing_related_provider_id` (run)

Some relation rows have no provider work ID.

**Evidence:** count=35 of 918 (3.8%)

**Action:** Do not use these rows as stable graph nodes until another identifier is available.

### MEDIUM — `edges_missing_related_title` (run)

Some relation rows have no related-paper title.

**Evidence:** count=41 of 918 (4.5%)

**Action:** Quarantine identity-empty rows or enrich them before canonical screening.

### MEDIUM — `openalex_api_key_not_recorded` (openalex)

The run manifest does not record use of an OpenAlex API key.

**Evidence:** openalex_mailto_used=False; openalex_api_key_used=field absent

**Action:** Use a current OpenAlex API key and record only a boolean, never the secret itself.

### MEDIUM — `semantic_scholar_api_key_not_used` (semantic_scholar)

The run was collected without a Semantic Scholar API key.

**Evidence:** semantic_scholar_api_key_used=false

**Action:** Use an API key for repair runs and preserve rate-limit/error diagnostics.

### MEDIUM — `unresolved_provider_seed` (P001/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\b63f06b66d8260a14d49a73be85f9351b523c17e2b8c775fa474eb45cb5428a0.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P003/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\0114edc4f9fff435a3293bd22cdf9cd874e59a350d2a16837a6de6e6e57355d7.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P004/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\d5f25fd403fedcb00fbce88b8e31dc3c1ba6b64d6fcb9970ceec30e99cae2250.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P005/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\f2204efbf8ab2a1ff9909fcbbadcff17ceb212f0521725172277ee061c2c0a6b.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P012/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\94b4d600c2c5b021cc24828eb338d5a3e18ac3d697dbf218ca09b93097785dce.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P013/openalex)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\1da96da04653a0c4312f56d56190de1c2d8d99fa8f56ea12e245a5dab172b1e4.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### MEDIUM — `unresolved_provider_seed` (P013/semantic_scholar)

The seed was not resolved by this provider.

**Evidence:** reason=unresolved; score=0.0000; cache=outputs\snowball_full_2026-07-05\cache\afe54d2a2c681524df676909d1c21f0669716d2176efb9b7ba69f54695115fcf.json

**Action:** Retry by stable identifier with credentials; retain as unresolved if no exact identity is found.

### LOW — `duplicate_title_year_node_groups` (run)

Multiple node rows share the same normalized title and year.

**Evidence:** groups=8

**Action:** Canonicalize by DOI/arXiv/PMID before title-year fallback and retain provider aliases.

### INFO — `cross_provider_duplicate_edges` (run)

The same canonical relation appears more than once across providers.

**Evidence:** redundant_provider_rows=154; canonical_related_identities=677

**Action:** Screen a canonical table while preserving provider-level provenance separately.

## Interpretation rule

This audit evaluates generated provider metadata, not scientific relevance. Passing it means the graph is structurally usable; it does not mean a citing paper actually used a dataset. Actual use must be verified during full-text screening.
