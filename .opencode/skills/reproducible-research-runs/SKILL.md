---
name: reproducible-research-runs
description: Create immutable, auditable research runs with manifests, input hashes, environment details, credentials-as-booleans, commands, counts, and verification results.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: reproducibility
---

Use a new run directory. Record:

- creation UTC;
- command and code version/commit;
- input files and SHA-256;
- Python and dependency versions;
- provider/API settings and non-secret key-use flags;
- limits, thresholds, retries, and cache policy;
- output row counts;
- warnings/errors;
- audit status.

Never store API keys. Never overwrite an accepted run. Keep raw provider payloads or stable cache references.
