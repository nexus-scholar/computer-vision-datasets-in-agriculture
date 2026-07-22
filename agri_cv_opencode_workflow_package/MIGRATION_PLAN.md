# Migration and research execution plan

## Principle

Do not reorganize everything at once. First create a reproducible baseline, then add a curated layer, then repair the graph, then screen papers.

## Phase 0 - Protect the current state

1. Make a filesystem backup.
2. Save `git status`, `git fsck --no-reflogs --unreachable`, and the current file manifest.
3. Do not overwrite `outputs/snowball_full_2026-07-05`.
4. Install this workflow overlay.
5. Create an initial Git commit containing code, prompts, small CSV inputs, documentation, and templates. Keep PDFs, API caches, and generated runs out of normal Git.

Exit criterion: `git status` is understandable and there is a recoverable baseline.

## Phase 1 - Establish sources of truth

Use this hierarchy:

1. `data/curated/` - human-reviewed decisions and synthesis; manuscript-grade evidence.
2. `config/` and seed manifests - controlled inputs.
3. `outputs/` - generated, immutable run artifacts; never automatically trusted.
4. `data/raw/` and local PDFs - immutable source material.
5. reports and narrative notes - interpretations that must cite curated evidence.

Remove duplicate source ambiguity gradually. Keep one tracked copy of each small source CSV and replace other copies with notes or manifests.

Exit criterion: every important table has one owner and one documented role.

## Phase 2 - Repair bibliographic identity

1. Apply P004 and P013 seed corrections.
2. Apply the collector hardening patch.
3. Add OpenAlex and Semantic Scholar API keys through environment variables, never committed files.
4. Rerun only unresolved, low-confidence, or incomplete seeds into a new run directory.
5. Audit the repair run.
6. Manually approve each seed-provider match in `seed_resolution_audit.csv`.

Acceptance rules:

- Exact DOI/arXiv/PMID/PMCID plus compatible title: accept.
- Exact normalized title plus compatible year and author: accept after review.
- Title score 0.88-0.94 without an identifier: manual review.
- Title score below 0.88: reject; do not collect relations.
- Any provider disagreement affecting identity: hold for human decision.

Exit criterion: every seed has an explicit status of `accepted`, `accepted_with_note`, `rejected`, or `unresolved`.

## Phase 3 - Build the canonical screening corpus

1. Use `build_accepted_graph.py` to select the newest exact human-accepted seed/provider identity across historical and repair runs.
2. Omit incomplete or identity-inconsistent provider pairs and preserve selected-run provenance.
3. Deduplicate by DOI, then arXiv, PMID/PMCID, then normalized title-year.
4. Preserve provider-specific IDs and counts in provenance columns.
5. Generate a blank screening queue with deterministic priority scores under a new `outputs/` run.
6. Quarantine papers sourced only through rejected seed matches.

Exit criterion: one generated canonical row per candidate paper, with traceable provider and seed relationships; no unreviewed queue is represented as curated evidence.

## Phase 4 - Human screening

Screen in batches of 10-20 papers. Free models should process one paper at a time or a very small batch.

Two-pass process:

- Title/abstract pass: include, exclude, or unclear.
- Full-text pass: determine dataset introduction, actual experimental use, benchmark use, methodological relevance, and limitations.

Never infer `actual_dataset_use` from the presence of a citation alone.

Exit criterion: every included paper has a human-reviewed decision and reason.

## Phase 5 - Evidence extraction

For each included paper, produce one human-readable evidence note and one normalized row. Extract:

- bibliographic identity
- dataset relationship
- task, modality, sensors, labels, scale, splits, metrics
- model and baselines
- robustness, missing-input, domain-shift, calibration, uncertainty, foundation-model use
- limitations and exact evidence locations
- implications for the research thesis

Exit criterion: no literature claim exists only in chat history.

## Phase 6 - Dataset opportunity ranking

Score each dataset on:

- data richness
- underutilization based on actual experimental use
- methodological novelty fit
- feasibility and access
- publication leverage

Keep raw sub-scores, evidence notes, and uncertainty. Do not hide judgment inside a single total.

Exit criterion: one primary dataset family and at most one secondary validation dataset are selected.

## Phase 7 - Freeze a falsifiable study protocol

1. Select one primary claim and primary endpoint.
2. Define the null hypothesis and minimum decisive experiment.
3. Freeze the dataset manifest, statistical unit, grouped split, baselines, metrics, seeds, compute budget, and stop-go gates.
4. Record the protocol in `data/curated/` and approve it before model development.

Exit criterion: the study can fail clearly and the failure would change the project decision.

## Phase 8 - Benchmark before architecture

Build grouped splits and strong baselines before full SARA-Net development. The first decisive comparison should test whether learned reliability improves over availability masks plus band dropout.

Exit criterion: the benchmark protocol is reproducible and simple baselines are credible.

## Phase 9 - SARA-Lite gate

Proceed to full SARA-Net only when SARA-Lite:

- preserves clean performance;
- improves missing/corrupted input robustness;
- produces reliability scores correlated with counterfactual band utility;
- improves or preserves calibration;
- survives grouped evaluation and multiple seeds.

Otherwise simplify the method or revise the reliability supervision.
