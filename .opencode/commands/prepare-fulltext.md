---
description: Build a bounded legal full-text acquisition queue from completed title/abstract decisions or a ranking CSV.
agent: fulltext-acquirer
subtask: true
---

Argument supplied: `$ARGUMENTS`

Determine the mode:
- When the argument ends in `.csv`, run:
  `agri-fulltext queue --ranking "$ARGUMENTS"`
- When the argument is a rank expression (e.g. `1-20`, `1,3,5`), run:
  `agri-fulltext queue --ranks "$ARGUMENTS"`
- When no argument is supplied, run:
  `agri-fulltext queue`

After creating the queue, inspect its manifest.
Stop if `validation_status` is not `passed`.
Only then run `resolve`.

1. Read `docs/workflow/FULLTEXT_WORKFLOW.md` and the legal acquisition skill.
2. Do not include an unfinished screening batch.
3. Run `agri-fulltext queue` with the appropriate mode.
4. Run `resolve` on the new queue but do not download.
5. Report candidate coverage by source, structured/PDF availability, rights-status warnings, identifiers missing, and the exact acquisition command. Do not enable OpenAlex content or unknown-rights flags.
