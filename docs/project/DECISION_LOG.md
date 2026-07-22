# Decision log

## 2026-07-22 — Adopt normalized screening event history

- Status: accepted
- Decision: use an append-only history plus a derived active snapshot.
- Evidence: the legacy rank-20 row was malformed and had overwritten the original decision; batch artifacts were incomplete.
- Alternatives: keep the 58-column file; manually patch individual rows.
- Risks: schema migration requires updated OpenCode instructions.
- Consequences: safer corrections, deterministic status, smaller model output, and auditable provenance.
- Owner: project owner
- Review date: after the next screening batch

## 2026-07-22 — Freeze current screening queue

- Status: accepted
- Decision: preserve ranks 1–560 until title/abstract screening is complete.
- Evidence: 60 rank-based decisions already exist; the graph has known but bounded S2 shortfalls.
- Alternatives: rebuild immediately with credentials.
- Risks: the queue is not citation-complete.
- Consequences: use it for discovery only, not coverage statistics.
- Owner: project owner
- Review date: after title/abstract screening
