# Repository map and ownership

```text
AGENTS.md                          Workspace rules loaded by OpenCode
opencode.json                     Permissions and context controls
.opencode/agents/                 Bounded specialist roles
.opencode/commands/               Thin repeatable commands
.opencode/skills/                 Reusable scientific procedures
config/                           Controlled protocols and seed corrections
data/raw/citation_exports/        Immutable report-derived citation tables
data/raw/seed_papers/             13 immutable PDFs plus identity/hash manifest
data/raw/api_archives/            Compressed historical provider-response caches
data/raw/migration_archives/      Exact pre-cleanup artifacts for audit only
data/curated/bibliography/        Seed/provider identity decisions
data/curated/screening/           History, active/enriched views, relevance, provenance
data/curated/evidence/            Full-text source-located evidence
data/curated/datasets/           Dataset registry and opportunity analysis
data/curated/claims/             Claim ledger and contradictions
data/curated/protocols/          Approved study protocols and amendments
outputs/snowball_*/               Immutable generated provider runs
outputs/accepted_graph_2026-07-22 Frozen graph snapshot used for screening
outputs/screening_queue_2026-07-22 Frozen rank-stable queue
outputs/screening_batches/        Prepared/finalized batch artifacts
scripts/research/                 Deterministic workflow utilities
src/agri_cv_novelty/              Shared Python logic
references/                       Preserved deep-research report
tools/agri_cv_snowball_package/   API collector and controlled seed manifest
```

## Ownership

- Raw: immutable source evidence.
- Generated: reproducible output; trusted only after an audit.
- AI-screened: provisional semantic judgment under the owner-authorized protocol.
- Curated/accepted: explicitly approved for synthesis.
- Narrative: must cite curated evidence or a primary source.

Do not maintain two active source-of-truth copies of the same table.
