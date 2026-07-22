---
description: Verify the local PDF corpus against the seed manifest and propose a stable mapping.
agent: corpus-curator
subtask: true
---

Load `local-corpus-integrity`, `bibliographic-resolution`, and `small-model-discipline`. Audit the PDFs and seed manifest named in `$ARGUMENTS`, or use the project defaults when no argument is supplied. Produce a preview of the corpus manifest, identity conflicts, duplicate hashes, missing seeds, unmapped files, and a non-destructive filename plan. Do not rename or delete PDFs.
