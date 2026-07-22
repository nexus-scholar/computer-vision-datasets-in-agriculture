# AI title/abstract screening protocol v1

## Question

Does the record justify full-text inspection for an agricultural computer-vision dataset, actual dataset use, benchmark design, or a methodological gap relevant to segmentation, multimodal/spectral sensing, 3D vision, robotics, robustness, generalization, calibration, uncertainty, or foundation-model adaptation?

Favor recall. Use `unclear` when the available abstract is insufficient.

## Decisions

- `include`: plausible full-text relevance.
- `exclude`: confidently outside scope.
- `unclear`: identity, abstract, scope, or dataset relationship is insufficient.

## Inclusion codes

- `I01` dataset introduction
- `I02` experimental dataset use
- `I03` dataset extension or relabeling
- `I04` benchmark/challenge/evaluation protocol
- `I05` relevant agricultural CV method
- `I06` multimodal, sensor-rich, temporal, spectral, depth, LiDAR, or 3D learning
- `I07` robustness, domain shift, cross-sensor, missing/corrupted input, or adaptation
- `I08` uncertainty, calibration, failure detection, or selective prediction
- `I09` meaningful foundation-model evaluation/adaptation
- `I10` useful review, taxonomy, or dataset survey

Multiple inclusion codes may be separated with `;`.

## Exclusion codes

- `E01_NOT_AGRICULTURE`
- `E02_NO_COMPUTER_VISION`
- `E03_NO_DATASET_RELEVANCE`
- `E04_NON_RESEARCH_ITEM`
- `E05_DUPLICATE`
- `E06_OUTSIDE_METHOD_SCOPE`
- `E07_WRONG_CITATION_CONTEXT`
- `E08_INVALID_OR_RETRACTED`

## Unclear codes

- `U01_NO_ABSTRACT`
- `U02_DATASET_USE_UNCLEAR`
- `U03_SCOPE_AMBIGUOUS`
- `U04_IDENTITY_AMBIGUOUS`
- `U05_INSUFFICIENT_METADATA`
- `U06_FULL_TEXT_REQUIRED`

## Controlled paper types

`dataset_paper`, `method_paper`, `benchmark_or_challenge`, `dataset_extension`, `application_paper`, `survey_or_review`, `foundation_model_study`, `domain_adaptation_study`, `robustness_study`, `agricultural_robotics`, `remote_sensing_study`, `phenotyping_study`, `other`, `unclear`.

## Controlled dataset relationships

`introduces_dataset`, `uses_dataset_experimentally`, `extends_dataset`, `benchmarks_dataset`, `pretrains_on_dataset`, `mentions_dataset_only`, `compares_datasets`, `no_dataset_relationship`, `unclear`.

A citation edge alone never proves experimental use.

## Relevance tags

Write semicolon-separated controlled tags in `relevance_yes` and `relevance_unclear`:

`semantic_segmentation`, `instance_segmentation`, `panoptic_segmentation`, `object_detection`, `classification`, `tracking`, `phenotyping`, `3d_vision`, `remote_sensing`, `uav`, `robotics`, `multispectral`, `hyperspectral`, `thermal`, `depth_or_rgbd`, `lidar_or_point_cloud`, `multimodal`, `multitemporal`, `domain_adaptation`, `cross_sensor`, `missing_modality`, `corrupted_input`, `uncertainty`, `calibration`, `failure_detection`, `foundation_models`.

Do not place a tag in both columns.

## Evidence and uncertainty

- Use only the prepared queue metadata, abstract, citation context, cached provider metadata, and already-local full text.
- Do not invent dataset names, tasks, modalities, identifiers, or access status.
- Use `named_datasets=unknown` when experimental use is plausible but the dataset name is not stated.
- Exclusions cannot have low confidence.
- Every row must preserve the prepared candidate ID, rank, title, batch ID, and queue hash.
