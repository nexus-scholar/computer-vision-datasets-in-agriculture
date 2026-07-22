# Package validation report

Validation date: 2026-07-22  
Target: supplied `repo-current.zip` state  
Result: **pass with repository-level warnings**

## Package checks performed

- Parsed `opencode.json` as valid JSON.
- Parsed every agent, command, and skill frontmatter block as YAML.
- Verified every skill directory matches its frontmatter `name`.
- Installed the overlay into a fresh copy of the repository with the non-destructive installer.
- Confirmed both source patches pass `git apply --check` against the supplied repository.
- Applied both patches to the fresh validation copy.
- Compiled the patched collector and all added Python scripts.
- Confirmed the patched collector exposes targeted-seed, API-key, match-threshold, and overwrite-safety options.
- Confirmed `inventory.py` can report an absolute output path after patching.
- Ran four package workflow tests successfully, covering low-confidence quarantine, cross-provider DOI canonicalization, newest exact accepted-run selection, and incomplete-relation omission.
- Ran the snowball audit against `outputs/snowball_full_2026-07-05`.
- Built a screening queue excluding P004 and verified deterministic row counts.
- Validated the accepted-graph builder on synthetic historical/repair runs.
- Ran a validation-only accepted-identity pass over the historical provider rows: 17 complete seed/provider pairs were included, 676 edges were retained, and the incomplete P007 Semantic Scholar pair was omitted with a high-severity issue. This was a software validation, not a human bibliographic approval.

## Historical-run validation results

- 918 provider edge rows audited.
- P004 identified as a critical false match and quarantined.
- Approximately 677 stable/canonical related-paper identities before seed quarantine.
- 154 cross-provider redundant edge rows detected per seed and direction.
- Screening build with P004 excluded: 677 edge rows read, 464 canonical papers written, 18 identity-empty rows quarantined.
- Overall historical-run quality gate: **fail until repair**.

## Repository warnings that remain after overlay installation

- There is no valid Git commit baseline.
- Three citation-export families have duplicate tracked/source copies.
- The historical P007 Semantic Scholar relation fetch is incomplete.
- The historical run must remain immutable and must not be treated as manuscript-grade evidence.

These warnings are intentionally not auto-fixed because they require a human decision about history, source ownership, or rerun provenance.

## Validation limitations

- The validation container did not include the OpenCode executable, so agent/skill/command discovery was checked by parsing JSON/YAML and matching the documented project conventions, not by launching an interactive OpenCode session.
- PowerShell was not installed, so `install.ps1` was reviewed statically; the underlying `install.py` workflow and both Git patch checks were executed successfully.
- API collection was not rerun because this package is a workflow and repair overlay; the historical outputs were audited locally and the collector patch was compile/help-tested.
