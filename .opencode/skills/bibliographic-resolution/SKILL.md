---
name: bibliographic-resolution
description: Validate scholarly-paper identity across DOI, arXiv, PMID/PMCID, title, year, authors, OpenAlex, and Semantic Scholar before collecting citation relations.
compatibility: opencode
metadata:
  project: agri-cv
  risk: critical
---

## Identity order

1. Exact DOI.
2. Exact arXiv ID.
3. Exact PMID/PMCID.
4. Exact normalized title plus compatible year and authors.
5. Fuzzy title search only as a candidate generator.

## Decisions

- `accepted`: exact identifier and compatible title.
- `accepted_with_note`: exact identity with non-material metadata disagreement.
- `manual_review`: title score 0.88-0.94 or incomplete author/year evidence.
- `rejected`: score below 0.88, material title/topic/year mismatch, or wrong document type.
- `unresolved`: no defensible candidate.

Never collect references/citations for `manual_review`, `rejected`, or `unresolved` seeds.

Record input identity, candidate identity, score, method, evidence URL, reviewer, date, and notes.
