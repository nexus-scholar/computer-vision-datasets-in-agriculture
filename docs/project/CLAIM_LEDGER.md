# Claim ledger

The machine-readable claim ledger lives at `data/curated/claim_ledger.csv`
(33 entries as of 2026-08-08). It is maintained through deterministic append
and correction scripts under `scripts/research/` (e.g.
`_append_ledger_entries.py`, `_reconcile_dso_claims.py`), never by hand-editing.

A claim cannot be used in a manuscript until it has:

- a stable claim ID;
- a precise statement and scope;
- one or more evidence IDs;
- an exact primary-source location;
- contradictory evidence when present;
- strength and uncertainty ratings;
- human approval and date.

Title/abstract screening decisions are not manuscript evidence.
