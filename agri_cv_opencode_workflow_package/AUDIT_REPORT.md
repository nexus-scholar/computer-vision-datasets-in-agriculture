# Audit of the attached repository state

Audit basis: the supplied `repo-current.zip`, including code, PDFs, CSVs, Git metadata, and `outputs/snowball_full_2026-07-05`.

## Executive assessment

The repository is a useful prototype, not yet a trustworthy research system. It has a sensible Python package, a locked environment, cached API responses, 13 readable seed PDFs, and a complete one-hop collection. The next step is not more collection. It is identity repair, provenance separation, and controlled human screening.

## Critical findings

### 1. Low-confidence matches are accepted as resolved

In the collector, `resolve_seed()` returns the best candidate even when its title score is below the threshold. The main loop checks only whether a record and provider ID exist, so it snowballs that candidate anyway.

Observed consequence:

- P004 input: `A Dataset for Semantic and Instance Segmentation of Modern Fruit Orchards ...`
- Accepted OpenAlex candidate: `Intelligent Fruit Yield Estimation for Orchards ... A Review`
- Match score: `0.3814`
- Wrong candidate year: 2021
- Polluted edges: 113 backward references and 128 forward citations

All P004-derived edges from the current run must be quarantined.

### 2. P013 is recoverable but the seed manifest is obsolete

The local `main.pdf` is a valid, readable TomatoPGT paper:

- Title: `TomatoPGT: A 3D point cloud dataset of tomato plants for segmentation and plant-trait extraction`
- DOI: `10.1016/j.dib.2026.112642`
- Data in Brief 66 (2026), article 112642

The seed manifest still contains a vague placeholder and an unhelpful Europe PMC-only identity. Patch it before rerunning.

### 3. The OpenAlex authentication instructions are outdated

The code and documentation support only `OPENALEX_MAILTO`. Current OpenAlex access requires a free API key. The collector should support `OPENALEX_API_KEY` while retaining `mailto` for contact/provenance.

## High-priority findings

### 4. Relation failures are silently converted to zero rows

P007 Semantic Scholar reports 65 references but downloaded 0. The relation iterator stops on an empty/error response without writing an error record. A run can therefore look complete while relations are missing.

### 5. There is no reliable Git baseline

The repository reports `No commits yet on master`, but `.git` is about 51 MB. This is likely tool-generated object history rather than a usable project history. Do not delete it blindly. Back up the repository, inspect unreachable objects, then create a clean initial commit or reinitialize Git if no useful refs exist.

### 6. Generated, raw, and curated evidence are not separated

- `outputs/` contains generated API results and is entirely ignored.
- There is no committed `data/curated/` area for human-reviewed decisions.
- The same citation CSVs exist in multiple locations.

Without a curated layer, an agent can accidentally treat raw provider metadata as established evidence.

### 7. Cross-provider deduplication is incomplete

Current run observations:

- 918 provider-level edges
- 689 node rows
- approximately 677 canonical related-paper identities using DOI/arXiv/PMID/PMCID/title-year fallback
- 154 cross-provider redundant edge rows when deduplicated per seed and direction
- 8 duplicate title-year node groups

Provider-level tables are useful for provenance, but screening should operate on a canonical paper table.

## Medium-priority findings

- 41 edges have no related title; 35 have no related provider ID.
- P002 and P008 have provider year disagreements, likely online-first versus issue-year records; preserve both dates instead of silently choosing one.
- Citation counts differ widely by provider, especially P011; do not average them or use them as stable truth.
- `inventory.py` writes an absolute manifest outside the repo, then crashes while printing `relative_to(root)`.
- The test suite contains one test and none for identity resolution, relation completeness, deduplication, or run auditing.
- The root uses `uv`, while the tool launchers create a second nested `.venv`; use one environment strategy.
- PDF filenames such as `main.pdf` and `1-s2.0-...pdf` are not stable research identifiers.
- `README.md` and `PROJECT_INDEX.md` describe a pre-run state and do not record the completed collection or known defects.
- `.agents/` and `.codex/` are empty, and there is no project-local OpenCode configuration.
- No `.env.example`, `CITATION.cff`, license, decision log, claim ledger, or screening protocol exists.

## What is already good

- All 13 seed PDFs are present, render correctly, and expose readable titles.
- The source report is preserved separately from generated outputs.
- Raw API responses and cache files were retained.
- A run manifest records provider selection, limits, and credential-use booleans.
- The Python package is small and compiles.
- The existing unit test passes under a compatible local Python environment.
- File hashing is already part of the inventory workflow.

## Required disposition of the current run

Treat `outputs/snowball_full_2026-07-05` as an immutable historical run.

- Do not delete it.
- Do not use P004 edges.
- Mark P007 Semantic Scholar references incomplete.
- Mark P013 unresolved.
- Generate a quality audit beside it.
- Run a new repair collection after patching the seed manifest and collector.
- Combine runs only through a deterministic canonicalization step that preserves provider provenance.
