# Research workflow

## Phase A — Bibliographic graph

1. Resolve seed identity.
2. Collect one-hop provider relations into a new dated run.
3. Audit identity and relation completeness.
4. Build a versioned accepted graph.
5. Build a versioned canonical queue.
6. Freeze that queue for one screening cycle.

## Phase B — Title/abstract screening

1. Prepare at most 20 unscreened rows with `prepare_screening_batch.py`.
2. Let the model fill only the prepared decision template using `config/screening_protocol_v1.md`.
3. Finalize with `finalize_screening_batch.py`.
4. The finalizer validates schema, identity, reason codes, tags, hashes, duplicates, history, active state, and status.
5. Never edit the active decision table manually.

## Phase C — Full-text evidence

1. Include all title/abstract `include` and `unclear` records.
2. Process one paper at a time.
3. Distinguish introduced, trained, evaluated, extended, repackaged, mentioned-only, and unclear dataset relationships.
4. Record page/section/table/figure locations.
5. Populate normalized evidence, dataset, method, and limitations tables.

## Phase D — Synthesis and study choice

1. Build actual-use counts, not citation counts.
2. Audit access, licensing, annotations, splits, leakage, modalities, and data quality.
3. Build a method-gap matrix.
4. Rank scientific opportunity separately from execution feasibility.
5. Select one primary dataset family and at most one secondary validation family.
6. Freeze a falsifiable protocol before architecture implementation.

## Current command

```text
/screen-paper 61-80
```
