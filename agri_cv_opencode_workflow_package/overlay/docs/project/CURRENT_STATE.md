# Current project state

Status: generated from the repository audit; update after each milestone.

## Available evidence

- 13 local seed PDFs.
- Deep research report and extracted citation CSVs.
- OpenAlex + Semantic Scholar one-hop run at `outputs/snowball_full_2026-07-05`.
- 694 backward provider rows, 224 forward provider rows, 918 provider edges, and 689 provider/canonical-ish nodes.

## Known blockers

- P004 was falsely resolved to an unrelated 2021 review; all P004 edges in the full run are quarantined.
- P013 seed identity is obsolete and must be patched to the 2026 TomatoPGT Data in Brief paper.
- P007 Semantic Scholar references are incomplete: 65 reported, 0 downloaded.
- Six seeds remain unresolved in Semantic Scholar in the historical run.
- OpenAlex API-key support is missing from the historical collector.
- The repository has no usable initial Git commit.

## Current objective

Produce an accepted seed-resolution table and a canonical, human-screenable paper queue. Do not expand snowball depth until this is complete.

## Next bounded action

Install the workflow package, apply the source patches, audit the historical run, patch P004/P013, and run a repair collection for P001, P003, P004, P005, P007, P012, and P013.

## Downstream gate

After the accepted screening corpus and dataset opportunity matrix exist, use `/design-study` to freeze one falsifiable benchmark protocol before SARA-Lite or full SARA-Net implementation.
