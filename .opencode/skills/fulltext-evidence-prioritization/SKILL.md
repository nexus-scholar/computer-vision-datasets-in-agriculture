---
name: fulltext-evidence-prioritization
description: Prioritize title/abstract-included agricultural computer-vision papers for lawful full-text acquisition, processing, and evidence extraction using transparent scientific value, project fit, information gain, access feasibility, estimated review cost, policy-weight sensitivity, and diversity-aware reranking. Use when deciding which included papers to retrieve or read first. Never use it to exclude papers automatically.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: fulltext-prioritization
  protocol: EVIDENCE_ROI_V1
---

# Purpose

Order the included title/abstract corpus so that early full-text work produces the greatest defensible research value per unit effort.

This skill is a **scheduling layer**, not another eligibility screen. It must preserve all active title/abstract inclusions.

# Why this is separate from dataset ranking

`dataset-opportunity-ranking` ranks datasets after source-located evidence exists. This skill ranks papers **before** full-text acquisition and evidence extraction. Its output helps decide which papers are most valuable to obtain and inspect first.

# Two-stage design

## Stage 1 — deterministic bootstrap

The Python workflow immediately ranks every active inclusion from already-curated fields:

- paper type and likely dataset relationship;
- project-relevance tags;
- abstract specificity;
- identity completeness;
- legal/open-access indicators;
- age-adjusted citation signal;
- seed/network breadth;
- likely processing difficulty.

Bootstrap values are scheduling estimates, not curated evidence.

## Stage 2 — bounded semantic refinement

An OpenCode model scores only prepared batches of at most 20 papers. The deterministic ranker then replaces bootstrap semantic fields for those papers while retaining bootstrap fallback values for all unscored papers.

A useful queue therefore exists immediately; all 260 papers do not need model scoring before full-text work begins.

# Required ranking views

Always preserve separate views:

1. `scientific_priority_rank` — expected scientific and project value.
2. `fast_roi_rank` — science moderated by lawful access and estimated reading cost.
3. `information_gain_rank` — high-impact questions whose uncertainty full text may resolve.
4. `recommended_fulltext_rank` — diversity-aware final scheduling queue.
5. `base_priority_rank` — pre-diversity strategic ordering.
6. Original title/abstract rank — retained as a baseline.

Never collapse them into one unexplained score.

# Semantic rubric

Score each semantic dimension as an integer from 0 to 4.

## project_fit

- 4: Directly informs robust agricultural segmentation, multispectral/multimodal reliability, missing or corrupted inputs, cross-sensor/domain shift, calibration, uncertainty, or failure detection.
- 3: Strong adjacent value: agricultural benchmark, foundation-model adaptation, domain adaptation, 3D/temporal phenotyping, multimodal sensing, or robust perception.
- 2: Useful agricultural-CV dataset or method context.
- 1: Peripheral background.
- 0: No meaningful connection. This should be rare because the paper is already included.

## dataset_evidence_value

- 4: Introduces or extends a high-value dataset, or provides detailed evidence about access, annotations, modalities, splits, quality, or under-exploitation.
- 3: Strong benchmark, comparative, or actual-use evidence.
- 2: Moderate dataset-use or dataset-quality evidence.
- 1: Descriptive mention likely useful only as context.
- 0: No dataset evidence.

## method_gap_value

- 4: Direct evidence about a major unaddressed gap: missing modalities, sensor reliability, corruption, cross-domain shift, calibration, uncertainty, leakage, or multimodal underuse.
- 3: Strong adjacent gap evidence.
- 2: General methodological evidence.
- 1: Limited gap relevance.
- 0: None.

## decision_leverage

- 4: Could change the primary dataset, central claim, benchmark protocol, architecture, or stop/go decision.
- 3: Could materially change an experiment, baseline set, or shortlist.
- 2: Can refine the literature argument.
- 1: Mostly contextual.
- 0: No plausible project decision impact.

## actual_use_likelihood

- 4: Abstract/metadata clearly show training, pretraining, benchmarking, or quantitative evaluation on a relevant dataset.
- 3: Strong evidence of actual use, but details require full text.
- 2: Possible actual use or dataset-paper baselines.
- 1: Likely descriptive mention only.
- 0: No dataset relationship.

A citation edge alone is never actual dataset use.

## evidence_specificity

- 4: Abstract contains concrete dataset scale, sensors/modalities, splits, methods, metrics, or comparative results.
- 3: Several concrete details.
- 2: Moderate specificity.
- 1: Vague claims.
- 0: No usable abstract evidence.

## information_uncertainty

This is value-of-information uncertainty, not generic model uncertainty.

- 4: A high-impact project question is unresolved and full text is likely to answer it.
- 3: Important ambiguity.
- 2: Moderate unknown.
- 1: Minor unknown.
- 0: The paper is already well understood from available evidence.

## estimated_reading_cost

Score 1–5:

- 1: Short, clear, structured dataset paper.
- 2: Normal paper with straightforward tables.
- 3: Moderate complexity or multiple experiments.
- 4: Long survey, multimodal/3D work, many tables/supplements, or weak extraction quality.
- 5: Very high-cost document requiring substantial manual acquisition or visual verification.

Cost must not suppress a decisive paper; the deterministic formula deliberately dampens cost.

# Controlled labels

`primary_role`:

- dataset_introduction
- dataset_extension
- experimental_dataset_use
- benchmark_or_challenge
- robustness_or_reliability_method
- multimodal_or_sensor_method
- domain_adaptation_method
- foundation_model_study
- segmentation_method
- 3d_or_phenotyping_method
- survey_or_review
- contextual_background
- other

`primary_theme`:

- multispectral_reliability
- crop_weed_segmentation
- plant_disease_segmentation
- dataset_quality_and_benchmarking
- multimodal_fusion
- missing_modality
- cross_sensor_or_domain_shift
- uncertainty_and_calibration
- foundation_models
- remote_sensing_uav
- orchard_robotics
- 3d_phenotyping
- temporal_phenotyping
- other

Use normalized concise labels for dataset, task, and modality clusters. Use `unknown` rather than guessing.

# Statistical safeguards

The deterministic workflow must:

- log-transform and age-adjust citation counts;
- percentile-normalize citation velocity, recency, and network breadth;
- give citation velocity only a small weight;
- retain multiple rank views;
- calculate Pareto layers over science, information gain, and feasibility;
- run seeded Monte Carlo sensitivity analysis over plausible weight and semantic-score perturbations;
- report mean/median rank, rank SD, and top-20/top-40/top-80 scenario frequencies;
- label those frequencies as **policy-weight stability**, not calibrated probabilities of scientific truth;
- diversity-rerank the final queue so one dataset or theme does not dominate the first block;
- retain all hashes, config values, and protocol version in a manifest.

# Workflow

1. Run `/bootstrap-ranking` once. This immediately ranks all active inclusions.
2. Use its `next_20_fulltext.csv` to start acquisition or review.
3. Run `/prepare-priority` to prepare the highest-priority unscored semantic batch.
4. Score one prepared batch with `/score-priority <batch-directory>`.
5. Rebuild with `/rank-fulltext`; unscored papers remain via bootstrap fallback.
6. Repeat semantic refinement only while it improves decision confidence or top-queue stability.
7. After at least 40 source-located full-text outcomes, use `/evaluate-ranking`.
8. Never revise weights automatically. Preserve v1 and create a new protocol version if evidence supports a change.

# Quality gates

Stop if:

- the included-corpus identity or queue hash changes unexpectedly;
- a requested paper is not an active title/abstract inclusion;
- a semantic batch exceeds 20 papers;
- identity fields are altered;
- a score lies outside its rubric range;
- an existing score is replaced without explicit supersession;
- the agent attempts to exclude or delete a paper;
- a curated CSV becomes malformed;
- deterministic validation fails.
