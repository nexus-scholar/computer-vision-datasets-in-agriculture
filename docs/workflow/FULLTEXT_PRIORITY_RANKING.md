# Full-text evidence-priority method

## 1. Objective

Maximize the amount of defensible, source-located research evidence obtained early from the 260 title/abstract-included papers, while preserving scientific diversity and never removing an included paper.

The target is not conventional citation relevance. The target is **evidence ROI for this project**:

- identify and characterize high-quality agricultural CV datasets;
- distinguish actual experimental dataset use from citation mentions;
- find repeated methodological gaps;
- prioritize evidence relevant to robust segmentation, multispectral/multimodal sensing, missing or corrupted inputs, sensor/domain shift, uncertainty, calibration, foundation-model adaptation, 3D vision, phenotyping, and robotics;
- obtain lawful full text efficiently.

## 2. Why the original screening rank is insufficient

The frozen screening queue’s original score was useful for finding likely relevant papers. It was not designed to schedule full-text work. It does not fully model:

- whether the paper can change a dataset or methodology decision;
- the likely value of resolving an uncertainty;
- lawful full-text availability;
- document-processing cost;
- redundancy among papers about the same dataset or theme;
- sensitivity to subjective project weights.

The original rank remains in every output as a baseline.

## 3. Two-stage scoring

### Deterministic bootstrap

Every active inclusion receives transparent estimates derived from already-curated metadata. The bootstrap is reproducible and costs no model calls.

It uses:

- `likely_paper_type`;
- `likely_dataset_relationship`;
- `named_datasets` and queue dataset names;
- vision task and modalities;
- project-relevance tags;
- abstract length and concrete numeric/detail indicators;
- decision confidence and unresolved fields;
- DOI/arXiv/PMID/PMCID/provider identities;
- open-access and PDF indicators;
- age-adjusted citation velocity;
- unique seed and edge breadth;
- document-complexity proxies.

Bootstrap values are scheduling estimates. They must not be cited as evidence about the paper.

### AI semantic refinement

A bounded OpenCode agent independently scores seven semantic dimensions and one cost dimension from the prepared paper metadata and abstract. Scores are append-only, validated, and versioned.

The hybrid ranker uses AI values when available and bootstrap fallback values otherwise. This means the queue remains complete at every stage.

## 4. Science score

All components are normalized to 0–1 before weighting:

```text
0.24 project fit
0.20 dataset evidence value
0.18 method-gap value
0.14 decision leverage
0.10 actual-use likelihood
0.06 evidence specificity
0.04 network breadth
0.02 age-adjusted citation velocity
0.02 recency
```

Citation signal is deliberately small. Venue prestige is not used.

## 5. Feasibility score

```text
0.45 lawful/open access likelihood
0.20 identifier completeness
0.15 abstract completeness
0.20 extraction ease
```

A difficult but decisive paper can still rank highly because feasibility is only one part of the strategic score and reading cost is damped.

## 6. Information gain

Information gain is the geometric mean of:

- project fit;
- decision leverage;
- important unresolved uncertainty.

The geometric mean prevents a paper from receiving a high information-gain score solely because it is ambiguous. An ambiguity matters only when it is relevant and decision-changing.

## 7. Fast ROI and base priority

Fast ROI moderates science by feasibility and estimated reading cost. Cost is bounded and damped.

The pre-diversity base priority combines:

```text
0.68 strategic value
0.32 fast ROI
```

Strategic value itself combines science, information gain, and feasibility.

## 8. Pareto analysis

Papers are assigned Pareto layers over:

- scientific score;
- information-gain score;
- feasibility score.

A Pareto-front paper is not dominated on all three dimensions. This prevents a single weighted total from hiding strategically important trade-offs.

## 9. Sensitivity analysis

Each ranking run performs 500 seeded policy scenarios by perturbing:

- science weights;
- feasibility weights;
- strategic weights;
- base-priority weights;
- semantic scores, with larger uncertainty for bootstrap values than AI-refined values.

For every paper it records:

- mean and median rank;
- rank standard deviation;
- frequency in the top 20, 40, and 80;
- stable, moderate, or unstable label.

These are **policy-weight stability frequencies**, not calibrated probabilities of scientific truth.

## 10. Diversity-aware recommendation

The final queue applies an MMR-style greedy reranking using tags for:

- dataset;
- seed-paper connection;
- paper role;
- research theme;
- task;
- modality.

Soft caps in the first 20 prevent one dataset or one theme from consuming the entire first review block.

## 11. Output tiers

Default scheduling tiers:

- Tier A: first 40 — decision-critical;
- Tier B: next 80 — high ROI;
- Tier C: remaining included papers — supporting and saturation coverage.

Tiers do not change inclusion status.

## 12. Prospective evaluation

After at least 40 source-located full-text outcomes, compare:

- recommended rank;
- science rank;
- fast-ROI rank;
- information-gain rank;
- original screening order.

Metrics:

- core precision and recall at 20/40/80;
- graded NDCG;
- cumulative evidence gain;
- papers to first core paper;
- normalized average time to core evidence;
- dataset/theme coverage.

Weights are never updated automatically. Preserve v1 before defining any v2 policy.
