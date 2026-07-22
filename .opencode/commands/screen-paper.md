---
description: Prepare, screen, validate, and finalize one bounded title/abstract batch.
agent: paper-screener
subtask: true
---

Screen ranks `$ARGUMENTS` from the frozen queue. When no ranks are supplied, process the next 10 unscreened records.

## Required procedure

1. Read `AGENTS.md`, `config/screening_protocol_v1.md`, and `docs/project/SCREENING_STATUS.md`.
2. Run:

```powershell
python scripts/research/screening_state.py validate --repo .
python scripts/research/prepare_screening_batch.py --repo . --ranks "$ARGUMENTS"
```

Omit `--ranks` when `$ARGUMENTS` is blank.

3. Read only the newly prepared batch's:

```text
input_rows.csv
screened_rows_template.csv
batch_manifest.json
```

4. Fill `screened_rows.csv` using the template's exact schema and fixed identity fields.
   - Maximum 20 rows.
   - Preserve candidate ID, rank, title, batch ID, and queue hash.
   - Use only controlled codes, paper types, relationships, and relevance tags from the protocol.
   - Set `model` to the actual selected model and `screened_at` to a UTC ISO timestamp.
   - Use `unknown` rather than guessing.
   - A citation edge is not experimental dataset use.

5. Finalize deterministically:

```powershell
python scripts/research/finalize_screening_batch.py <new-batch-directory> --repo .
python scripts/research/screening_state.py validate --repo .
python scripts/research/check_research_repo.py --repo .
```

6. Stop without finalizing if validation fails. Do not hand-edit the active decisions file, status counts, or batch provenance.

## Final response

Report only:

```text
Batch:
Ranks:
Included:
Excluded:
Unclear:
Validation:
Files created/updated:
Warnings:
Next command:
```
