---
name: systematic-screening
description: Apply the controlled agricultural-CV title/abstract or full-text screening protocol without conflating citations, dataset mentions, and actual experimental use.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: literature-review
---

## Title/abstract stage

Read `config/screening_protocol_v1.md`. Favor recall, but remain evidence-bound. Use only controlled codes and relevance tags. Preserve prepared identity fields. Use `unclear` when metadata or scope is insufficient.

## Full-text stage

Distinguish:

- introduced;
- used for training;
- used for evaluation;
- used for pretraining;
- extended;
- repackaged;
- benchmarked;
- compared descriptively;
- mentioned only;
- unclear.

Actual use requires full-text evidence. Record page, section, table, figure, or appendix. Separate observed facts, author claims, and reviewer inference.
