---
description: Combine repaired and historical runs using only human-accepted seed/provider identities.
agent: workflow-maintainer
subtask: true
---

Load `bibliographic-resolution`, `snowball-quality-audit`, `reproducible-research-runs`, and `small-model-discipline`. For the run directories and seed audit in `$ARGUMENTS`, preview the exact command for `build_accepted_graph.py`. Runs must be ordered oldest to newest. Do not include unresolved, rejected, identity-mismatched, or silently incomplete seed/provider pairs. Report selected run provenance and the output quality gate.
