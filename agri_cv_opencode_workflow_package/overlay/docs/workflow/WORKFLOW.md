# Research workflow

## Data zones

### Raw

Immutable material: PDFs, source exports, raw API JSON, and API cache. Raw files are never edited in place.

### Generated

Run-specific API and deterministic analysis output under `outputs/<run-id>/`. Generated output is reproducible but not automatically trusted.

### Curated

Human-reviewed evidence under `data/curated/`. Curated tables are the only source for synthesis, opportunity scoring, and manuscript claims.

## Required run naming

Use `outputs/<operation>_YYYY-MM-DD[_HHMM]/`. Each run must contain a manifest with input hashes, command, environment, provider settings, limits, and counts.

## Screening sequence

1. seed identity audit;
2. human seed/provider acceptance;
3. accepted graph construction across immutable runs;
4. canonical deduplication;
5. title/abstract screening;
6. full-text screening;
7. paper evidence extraction;
8. dataset registry update;
9. opportunity matrix;
10. claim ledger;
11. dataset selection decision;
12. approved study protocol;
13. benchmark and method gate.

## Review ownership

Agents may propose. Humans accept or reject. Record the reviewer and date in every curated table.

## Experimental-design rule

Do not begin full architecture work until an approved study protocol records the primary claim, null hypothesis, grouped split, simple and capacity-matched baselines, primary endpoint, statistics, compute budget, and stop-go rules.
