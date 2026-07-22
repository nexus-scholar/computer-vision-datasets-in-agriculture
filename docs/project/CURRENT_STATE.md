# Current project state

Last reconciled: 2026-07-22

## Completed

- Repository workflow and Git baseline established by the project owner.
- P004 false OpenAlex match repaired; historical P004 edges remain quarantined from the frozen accepted graph.
- P013 resolved as the 2026 TomatoPGT Data in Brief paper.
- OpenAlex/Semantic Scholar one-hop collection, repair run, and S2 retry preserved.
- Accepted graph snapshot built with 869 provider relations.
- Canonical screening queue frozen at 560 candidates.
- Title/abstract screening completed for ranks 1–60.
- Active decisions: 55 include, 5 exclude, 0 unclear.
- Rank 20 correction is preserved as a superseding event rather than an in-place overwrite.
- Screening state migrated to a normalized and deterministically validated schema.

## Known limitations

1. The accepted graph was built with `allow_incomplete_relations=true` and therefore failed its completeness gate.
2. Semantic Scholar backward references are incomplete for P001 and P007.
3. Semantic Scholar identities remain unresolved for P003 and P004; OpenAlex identities are accepted and sufficient for the frozen queue.
4. The legacy seed-resolution table lacks named reviewer and review timestamp metadata.
5. Title/abstract decisions are AI-screened and provisional; actual dataset use remains unverified until full text.
6. A high include rate is expected under the recall-first protocol, but it makes disciplined full-text exclusion essential.

## Frozen-state rule

Do not rebuild or re-rank `outputs/screening_queue_2026-07-22/` during the current title/abstract phase. A later graph refresh must create a new queue version and map existing decisions by `candidate_id`, not by rank.

## Exact next action

```text
/screen-paper 61-80
```

Before and after the batch:

```powershell
python scripts/research/screening_state.py validate --repo .
```

## Downstream gate

Do not run dataset opportunity ranking or `/design-study WeedsGalore` until full-text evidence distinguishes dataset introduction, experimental use, descriptive mention, modality usage, split quality, robustness testing, and access/licensing.
