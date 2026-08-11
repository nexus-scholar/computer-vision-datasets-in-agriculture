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

## 2026-08-08 — Supersede rank-based dataset claims from pre-refresh universes

- Status: accepted (AI-provisional; awaiting human confirmation)
- Decision: mark DSO-001, DSO-002, DSO-003, DSO-005 as superseded and append DSO-019 recording the closed-universe top-20 dataset list.
- Evidence: `outputs/dataset_opportunity_scores.csv` (96 rows, ranks 1–96) recomputed against the closed 190-paper universe; `outputs/dataset_registry.csv`.
- Reason: the four claims stated ranks computed against the earlier 30/51-dataset universes and no longer hold. Concretely: DSO-001 said AgroVG leads (now rank 2 behind MuST-C 24.5); DSO-002 said PhenoBench rank 2 (now rank 6); DSO-003's named datasets drifted to ranks 11–25; DSO-005 said ROSE-X is the top 3D dataset (now rank 26). MuST-C (DSO-004) still verifies.
- How: deterministic script `scripts/research/_reconcile_dso_claims.py`; ledger grew 27 → 33 rows.
- Consequences: stale rank claims must not be cited; dataset selection must use DSO-019's top-20 list.
- Owner: project owner
- Review date: before the experimental-design-gates phase
