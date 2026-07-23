FULLTEXT_QUEUE_FIELDS = [
    "paper_id", "rank", "title", "year", "authors", "venue", "doi", "arxiv_id", "pmid", "pmcid",
    "openalex_id", "semantic_scholar_id", "landing_url", "pdf_url", "is_open_access",
    "screening_decision", "screening_confidence", "likely_paper_type", "priority_score",
    "acquisition_status", "structured_status", "pdf_status",
    "acquisition_batch_id", "ranking_position", "ranking_run_id",
    "ranking_source_sha256", "notes",
]

CANDIDATE_FIELDS = [
    "candidate_id", "paper_id", "source", "artifact_type", "score", "url", "discovery_method",
    "license", "version", "host_type", "rights_status", "is_oa", "expected_cost_usd", "metadata",
]

ATTEMPT_FIELDS = [
    "attempt_id", "run_id", "paper_id", "candidate_id", "source", "artifact_type", "url",
    "started_at", "completed_at", "status", "http_status", "final_url", "content_type", "size_bytes",
    "sha256", "stored_path", "license", "version", "rights_status", "error",
]

RESOLVER_ERROR_FIELDS = [
    "error_id", "run_id", "paper_id", "source", "error", "recorded_at",
]

ARTIFACT_REGISTRY_FIELDS = [
    "artifact_id", "paper_id", "rank", "title", "source", "artifact_type", "stored_path", "sha256",
    "size_bytes", "mime_type", "source_url", "final_url", "license", "version", "host_type",
    "rights_status", "acquired_at", "run_id", "candidate_id", "status", "notes",
]

EXTRACTION_REGISTRY_FIELDS = [
    "extraction_id", "paper_id", "rank", "title", "source_sha256", "source_artifact_type",
    "output_dir", "docling_status", "grobid_status", "publisher_xml_status", "preflight_class",
    "qa_status", "processor_version", "created_at", "run_id", "manifest_sha256", "notes",
]

QUALITY_REVIEW_FIELDS = [
    "review_id", "paper_id", "extraction_id", "decision", "text_quality", "layout_quality",
    "table_quality", "figure_quality", "reference_quality", "page_grounding_quality",
    "preferred_text_source", "needs_visual_review", "reviewer", "reviewed_at", "notes",
]

SELECTION_FIELDS = [
    "acquisition_batch_id", "ranking_position", "candidate_id",
    "original_screening_rank", "title", "priority_score", "ranking_run_id",
]

ACQUISITION_BATCH_FIELDS = [
    "batch_id", "ranking_source", "ranking_source_sha256", "queue_path",
    "queue_sha256", "selection_policy", "requested_limit", "source_row_count",
    "effective_limit", "selected_count", "skip_complete", "validation_status",
    "created_at", "notes",
]

FULLTEXT_DECISION_FIELDS = [
    "fulltext_screening_id", "paper_id", "rank", "title", "extraction_id", "decision",
    "reason_code", "paper_role", "actual_dataset_use", "dataset_relationship", "named_datasets",
    "evidence_summary", "source_page", "source_section", "source_table", "source_figure",
    "reviewer", "reviewed_at", "supersedes_fulltext_screening_id", "notes",
]
