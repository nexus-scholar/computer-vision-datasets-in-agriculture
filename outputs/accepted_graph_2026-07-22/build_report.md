# Accepted graph build report

Generated: 2026-07-22T14:39:01.618935+00:00

Quality gate passed: **False**

## Counts

- Human-accepted seed/provider pairs: 24
- Included pairs: 24
- Omitted pairs: 0
- Accepted relation rows: 869
- Critical/high issues: 2

## Rule

The newest supplied run is used only when its exact provider identity matches the human audit. Incomplete or identity-inconsistent pairs are omitted unless incomplete relations were explicitly allowed.

## Issues

Critical: 0 · High: 2 · Medium: 0 · Low: 0

### HIGH — relation_count_shortfall (P001/semantic_scholar)

The selected accepted identity has incomplete downloaded citation relations.

Evidence: backward: downloaded=0, expected=47, reported=47, cap=0

Action: Rerun the relation fetch with credentials and inspect relation_errors.csv; include only with an explicit incomplete-data decision.

### HIGH — relation_count_shortfall (P007/semantic_scholar)

The selected accepted identity has incomplete downloaded citation relations.

Evidence: backward: downloaded=0, expected=65, reported=65, cap=0

Action: Rerun the relation fetch with credentials and inspect relation_errors.csv; include only with an explicit incomplete-data decision.
