# Screening decision log

## 2026-07-22 — Normalize title/abstract screening state

- Status: accepted migration
- Decision: separate append-only decision history, active decisions, and derived relevance tags.
- Reason: the legacy CSV was malformed at rank 20, rank 20 had been overwritten rather than superseded, batch 002 lacked a screened-row snapshot, and batch 003 lacked a CSV header.
- Consequence: future screening must use deterministic prepare/finalize scripts; direct edits to active decisions are prohibited.

## 2026-07-22 — Preserve the frozen queue

- Status: accepted
- Decision: continue screening queue version `2026-07-22` despite documented P001/P007 S2 relation shortfalls.
- Reason: rank continuity preserves completed work; the graph remains useful for candidate discovery but not for complete bibliometric claims.
- Reversal condition: create a new versioned queue after a credentialed graph refresh and map decisions by canonical candidate ID.
