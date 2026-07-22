# Preserved progress manifest

This document states the research progress that the clean replacement must preserve.

## Bibliography and snowballing

- 13 seed papers and their local PDFs.
- P004 corrected to the Modern Fruit Orchards CVPRW 2025 paper.
- P013 corrected to TomatoPGT, DOI `10.1016/j.dib.2026.112642`.
- Full OpenAlex/Semantic Scholar run from 2026-07-05.
- Targeted repair run from 2026-07-22.
- Semantic Scholar retry run from 2026-07-22.
- Accepted graph snapshot with 869 relations.
- Frozen canonical queue with 560 candidates and SHA-256 `feb7c8a80978b97f3bdcffd7291708e8ac5282301ce06c793247227bc43712be`.

## Screening

- Active ranks: 1–60.
- Active decisions: 55 include, 5 exclude, 0 unclear.
- Append-only history events: 61.
- Rank 20 active decision: exclude, preserving the earlier include as the superseded event.
- Next rank range: 61–80.

## Quality limitations retained

- Incomplete Semantic Scholar backward-reference relations for P001 and P007.
- Missing legacy reviewer metadata in the seed-resolution table.
- AI-only title/abstract judgments are provisional.
- Full-text evidence extraction has not started.

## Verification commands

```powershell
python scripts/research/screening_state.py validate --repo .
python scripts/research/check_research_repo.py --repo .
python -m pytest -q
```
