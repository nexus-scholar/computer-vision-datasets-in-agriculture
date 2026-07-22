---
name: dataset-opportunity-ranking
description: Rank agricultural CV datasets using transparent evidence-based sub-scores for richness, underuse, novelty fit, feasibility, and publication leverage.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: strategy
---

## Dimensions

Score each 0-5 with evidence:

- Data richness: modalities, labels, diversity, metadata, temporal/spatial structure.
- Underuse: actual experimental uses, depth of use, strength of existing baselines.
- Novelty fit: missing-input robustness, sensor conditioning, multimodal fusion, domain shift, calibration, 3D/temporal opportunities.
- Feasibility: access, license, size, formats, compute, split quality.
- Publication leverage: clear scientific importance, gap clarity, broader CV relevance.

Do not use citation count alone as underuse. Preserve confidence and disqualifying risks. Select one primary and at most one secondary dataset family.
