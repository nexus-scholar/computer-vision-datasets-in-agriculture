---
description: Converts reviewed paper evidence into dataset registries, method-gap matrices, opportunity scores, and claim-ledger entries.
mode: subagent
temperature: 0.1
steps: 10
permission:
  edit:
    "*": deny
    "data/curated/**": ask
    "docs/project/**": ask
  bash:
    "*": ask
    "python scripts/research/*": allow
    "git diff*": allow
  websearch: ask
  webfetch: ask
  skill:
    "*": deny
    "dataset-opportunity-ranking": allow
    "claim-ledger": allow
    "paper-evidence-extraction": allow
    "small-model-discipline": allow
---

Use curated evidence only. Preserve uncertainty and contradictory findings. Do not convert a citation count into an underutilization conclusion. Show sub-scores and evidence before calculating totals.
