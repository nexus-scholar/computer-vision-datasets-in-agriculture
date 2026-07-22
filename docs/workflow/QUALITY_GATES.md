# Quality gates

## Gate 1 — Seed identity

Required before using a seed/provider pair:

- exact stable identifier or manually verified title/author/year match;
- explicit status;
- provider disagreement documented;
- provenance source recorded.

Legacy rows without reviewer metadata may support discovery when identifiers are exact, but must be manually verified before manuscript bibliography use.

## Gate 2 — Relation completeness

Required before citation-coverage or bibliometric claims:

- no accepted wrong identity;
- no unexplained provider shortfall;
- manifest, relation errors, and raw records preserved;
- quarantined seeds excluded.

The current graph does **not** pass this gate because P001 and P007 S2 references are incomplete. It is conditionally usable for screening only.

## Gate 3 — Canonical queue

Required before screening:

- stable canonical paper ID;
- cross-provider provenance preserved;
- empty identities quarantined;
- queue version frozen after screening starts.

The 2026-07-22 queue passes this operational gate.

## Gate 4A — AI title/abstract screening

Required for each finalized batch:

- at most 20 records;
- valid controlled decision and reason code;
- no low-confidence exclusion;
- candidate ID and title match the frozen queue;
- batch and queue hashes recorded;
- append-only decision history;
- active state rebuilt and validated.

## Gate 4B — Full-text evidence

Required before synthesis:

- actual dataset relationship verified from full text;
- source location recorded;
- uncertainty explicit;
- access/license evidence recorded where relevant;
- human confirmation for central evidence.

## Gate 5 — Dataset ranking

Required before choosing an experiment:

- dataset registry deduplicated;
- actual use separated from mentions;
- method gaps supported across papers;
- data quality, leakage, license, and feasibility documented;
- scientific and execution scores shown separately.

## Gate 6 — Research claim and study protocol

Required before implementation or manuscript use:

- one primary claim and null hypothesis;
- grouped split and leakage controls;
- strongest simple and capacity-matched baselines;
- primary endpoint and statistical unit;
- calibration/robustness metrics where claimed;
- compute budget, ablations, and stop/go rules;
- human approval.
