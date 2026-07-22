---
name: experimental-design-gates
description: Turn curated evidence into a minimal, falsifiable agricultural-CV study protocol with leakage controls, strong baselines, statistics, compute limits, and predeclared stop-go decisions.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: experimental-design
---

## Required study contract

Record:

- one primary scientific claim and one primary endpoint;
- null and alternative hypotheses;
- selected dataset version, license, access state, and immutable manifest;
- statistical unit and grouped split rule;
- strongest simple baseline and parameter/compute-matched comparator;
- minimum decisive experiment;
- robustness conditions and corruption-generation provenance;
- metrics, confidence intervals, multiple-comparison handling, and seeds;
- ablations tied to specific causal questions;
- compute budget and termination rule;
- explicit pass, revise, and stop criteria;
- threats to validity and evidence still missing.

## Non-negotiable controls

- No random tile leakage across the same field, orthomosaic, plant, sequence, or acquisition campaign.
- No derived index may retain information from a supposedly removed raw band.
- Clean performance and degradation curves must both be reported.
- Reliability must be validated against observed utility or known corruption, not only visualized.
- A wider or parameter-matched baseline is required when the proposed model has materially greater capacity.
- Optional extensions cannot be used to rescue a failed primary hypothesis.

Prefer the smallest experiment that could prove the method unnecessary. That is the correct first experiment.
