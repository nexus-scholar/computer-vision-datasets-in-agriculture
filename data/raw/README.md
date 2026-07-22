# Raw evidence zone

Raw bytes are immutable.

- `citation_exports/`: report-derived source tables.
- `seed_papers/`: identity-mapped PDFs plus SHA-256 manifest.
- `api_archives/`: compressed historical provider-response caches removed from active run directories to reduce clutter.
- `migration_archives/`: exact pre-cleanup artifacts retained for audit only; never use them as active state.

Corrections belong in `config/` or curated decision tables. Never edit an archived provider response or PDF in place.
