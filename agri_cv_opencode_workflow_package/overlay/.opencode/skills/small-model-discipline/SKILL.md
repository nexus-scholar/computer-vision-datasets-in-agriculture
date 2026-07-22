---
name: small-model-discipline
description: Keep free or smaller models reliable by constraining scope, inputs, outputs, batch size, verification, and stop conditions.
compatibility: opencode
metadata:
  project: agri-cv
  risk: general
---

## Task contract

Before acting, state:

1. one objective;
2. exact files/rows to read;
3. exact output path and schema;
4. maximum batch size;
5. evidence standard;
6. stop conditions;
7. verification command.

Do not broaden scope during execution. Use `unknown` rather than guessing. Preview edits. End with one exact next action.
