---
name: method-gap-analysis
description: Build a structured method-gap matrix from included full-text papers, tagging each on split rigor, baseline strength, calibration, cross-sensor testing, code availability, and dataset role.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: evidence-synthesis
---

## When to use

After full-text screening decisions are finalized for a batch. Run on all included papers (core + supporting) to produce a method-gap matrix that reveals systematic weaknesses in the literature and guides experiment design.

## Taxonomy (6 dimensions)

### 1. `split_level` — How train/test data was separated
| Tag | Meaning |
|---|---|
| `random` | Random split, likely leakage across fields/plants/time |
| `grouped_field` | Entire fields held out |
| `grouped_plant` | Entire plants/individuals held out |
| `grouped_time` | Temporal split (different days/seasons) |
| `grouped_location` | Different farms/regions held out |
| `unclear` | Not specified or can't determine |

### 2. `baseline_strength` — Comparison rigor
| Tag | Meaning |
|---|---|
| `strong_simple` | Includes simple baselines (RF, SVM, vanilla CNN, thresholding) alongside deep/SOTA |
| `sota_only` | Only compares against other deep learning methods |
| `none` | No comparison at all |
| `unclear` | Can't determine |

### 3. `calibration_reported` — Uncertainty awareness
| Tag | Meaning |
|---|---|
| `yes` | ECE, reliability diagrams, confidence curves, Brier score reported |
| `partial` | Some mention (prediction intervals, Bayesian, MC dropout) but no rigorous calibration metrics |
| `no` | Not discussed |

### 4. `cross_sensor_test` — Generalization evidence
| Tag | Meaning |
|---|---|
| `same_sensor` | Trained and tested on same camera/sensor |
| `cross_sensor` | Explicitly tested on different camera/sensor |
| `cross_dataset` | Tested across datasets/domains |
| `both` | Both cross-sensor and cross-dataset |
| `unclear` | Not specified |

### 5. `code_available` — Reproducibility
| Tag | Meaning |
|---|---|
| `public` | Code publicly available with URL |
| `weights_only` | Only model weights/model released |
| `not_available` | Not released / not mentioned |
| `not_applicable` | Dataset paper (no code expected) |

### 6. `dataset_role` — How the dataset is used
| Tag | Meaning |
|---|---|
| `introduced` | Paper introduces a new dataset |
| `used_training` | Uses existing dataset for training |
| `used_evaluation` | Uses existing dataset for evaluation |
| `extended` | Extends/repackages existing dataset |
| `benchmarked` | Benchmarks methods on dataset |
| `unclear` | Can't determine |

## Workflow

### Phase 1 — Structured data extraction (deterministic, no LLM)

Run `scripts/research/method_gap_extract_structured.py` to pull from `extraction_registry.csv`, `full_text_decisions.csv`, `manifest.json`, and QA files. Outputs: `outputs/method_gap_matrix.csv` with all columns except the 6 tags.

```powershell
python scripts/research/method_gap_extract_structured.py --repo .
```

### Phase 2 — Tagging (LLM judgment from evidence)

1. **Evidence extraction**: run `scripts/research/method_gap_evidence.py` to scan each paper's `paper.md` for dimension-relevant patterns and extract context snippets.
2. **Batch tagging**: split papers into batches of ≤10. For each batch, have an agent read the evidence CSV and `paper.md` (when evidence is ambiguous) then assign tags per the taxonomy above.
3. **Merge**: run `scripts/research/method_gap_merge.py` to combine batch results and produce the final matrix with gap summary statistics.

### Required input files

- `data/curated/screening/full_text_decisions.csv` — decisions with `paper_id`, `decision`, `rank`, `title`
- `data/curated/fulltext/extraction_registry.csv` — extraction records with `output_dir`
- Per-paper: `{output_dir}/llm/paper.md` and `{output_dir}/manifest.json`

### Output

`outputs/method_gap_matrix.csv` — one row per included paper, 38 columns (32 structured + 6 tags + confidence notes).

## Non-negotiable rules

- Never change screening decisions or extraction records.
- When evidence is empty or ambiguous, always read the full `paper.md` before assigning `unclear`.
- A dataset paper (`dataset_role=introduced`) can still have `split_level`, `baseline_strength`, etc. from its demonstration experiments — read that section too.
- Deduplicate by `paper_id` before counting or summarizing.
- After merge, verify all 6 tag columns have zero empty cells.
- Preserve `confidence_notes` for borderline or uncertain tags.
