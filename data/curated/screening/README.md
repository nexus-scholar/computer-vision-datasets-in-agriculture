# AI-screened title/abstract decisions

The project owner authorizes autonomous AI title/abstract screening. These decisions remain provisional until full-text evidence or a human confirmation gate.

## Active files

| File | Purpose |
|---|---|
| `title_abstract_decision_history.csv` | Append-only event history, including superseded decisions |
| `title_abstract_decisions.csv` | Derived active decision per candidate |
| `title_abstract_relevance.csv` | Derived wide relevance-tag table |
| `title_abstract_decisions_enriched.csv` | Read-only joined view with queue metadata and wide relevance fields |
| `screening_batches.csv` | Batch paths, hashes, counts, and provenance quality |

## Rules

- Never edit the active file directly.
- New batches are prepared and finalized through deterministic scripts.
- Corrections must name the exact `supersedes_screening_id`.
- A citation mention is not actual dataset use.
- `unknown` is a valid scientific result; guessing is not.
- Full-text evidence must record page, section, table, or figure locations.
