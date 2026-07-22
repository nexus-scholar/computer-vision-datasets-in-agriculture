# Repository map and ownership

```text
AGENTS.md                         Project rules loaded by OpenCode
opencode.json                    Permission and context-control policy
.opencode/
  agents/                        Bounded specialist roles
  commands/                      Repeatable TUI workflows
  skills/                        Reusable scientific procedures
config/                          Controlled research inputs and corrections
data/
  raw/                           Immutable source exports and local-source manifests
  curated/
    bibliography/                Human-approved seed identities and accepted graph decisions
    screening/                   Human-reviewed title/abstract and full-text decisions
    evidence/                    One-paper evidence notes and normalized extraction rows
    datasets/                    Dataset registry and opportunity matrix
    claims/                      Claim ledger and contradiction tracking
    protocols/                   Approved study protocols and experiment decisions
    templates/                   Blank schemas only
outputs/                         Immutable generated runs, audits, and intermediate builds
scripts/research/                Deterministic quality-control and graph-building utilities
docs/project/                    Current state, decisions, claims, and session handoff
docs/workflow/                   Workflow, gates, model protocol, and this map
tools/agri_cv_snowball_package/  Provider collector and its controlled inputs
```

## Ownership rule

- Raw: source owner; never edited in place.
- Generated: script/run owner; reproducible but untrusted until audited.
- Curated: named human reviewer; authoritative for synthesis.
- Narrative: research lead; must point to curated evidence or primary sources.

Do not keep two active source-of-truth copies of the same CSV. Duplicate raw copies may remain temporarily for provenance, but one owner path must be declared before synthesis.
