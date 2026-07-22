# Curated full-text state

This directory stores small, auditable registries and quality decisions. It does not store PDF bytes.

- `artifact_registry.csv`: append-only successful acquisition/import events.
- `extraction_registry.csv`: append-only processing events tied to source hashes.
- `fulltext_quality_reviews.csv`: reviewer decisions on extraction quality.

Never infer reuse rights from “free to read.” Keep license and rights status separate. Never rewrite a source hash or silently replace an artifact event.

## Durable audit tables

- `artifact_registry.csv`: successful immutable artifacts.
- `fetch_attempt_registry.csv`: every download success, failure, rights skip, and cooldown skip.
- `resolver_error_registry.csv`: source-resolution failures, with secrets redacted.
- `extraction_registry.csv`: parser runs and QA state.

Run-local copies remain under `outputs/fulltext/`; the curated registries preserve the lightweight audit trail even when generated outputs stay out of Git.
