---
description: Build a canonical screening queue from an audited run.
agent: workflow-maintainer
subtask: true
---

For run `$ARGUMENTS`, confirm the audit passes or identify quarantine seed IDs. Run `prepare_screening_queue.py` using only accepted seeds. Write the generated blank queue under a new `outputs/screening_queue_<date>/` directory, not in `data/curated/`. Report canonical row counts, duplicates collapsed, excluded/quarantined rows, and the output path. Human decisions are written later to `data/curated/screening/`.
