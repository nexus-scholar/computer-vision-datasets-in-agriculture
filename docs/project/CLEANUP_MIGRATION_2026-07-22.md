# Cleanup migration map

## Canonical path changes

| Previous path | Replacement | Treatment |
|---|---|---|
| `datasets-papers-2026-07-03/*.pdf` | `data/raw/seed_papers/Pxxx_<slug>.pdf` | Moved and hash-mapped |
| `datasets-papers-2026-07-03/*.csv` | `data/raw/citation_exports/` or `tools/.../input/` | Duplicate copy removed |
| `outputs/snowball_*/cache/` | `data/raw/api_archives/snowball_api_caches_2026-07-22.zip` | Consolidated with entry manifest |
| malformed `title_abstract_decisions.csv` | normalized history/active/relevance/enriched tables | Migrated without changing active decisions |
| missing/headerless batch snapshots | rebuilt batch artifacts | Reconstructed and explicitly labeled |
| `agri_cv_opencode_workflow_package/` | installed `.opencode/`, scripts, docs, and configuration | Duplicate installer source removed |
| nested snowball `.venv` behavior | root `uv` project | Unified environment |

## Files intentionally retained as historical outputs

The three provider runs, their summary CSVs, raw seed records, graph audits, frozen accepted graph, and frozen screening queue remain in `outputs/`. They are generated evidence, not curated conclusions.

## Audit-only archives

- `data/raw/api_archives/snowball_api_caches_2026-07-22.zip`
- `data/raw/migration_archives/pre_cleanup_screening_state_2026-07-22.zip`

These archives must not be used as active workflow inputs unless an explicit restoration is documented.
