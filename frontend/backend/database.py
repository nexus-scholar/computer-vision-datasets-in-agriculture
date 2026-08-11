import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CURATED_DIR = REPO_ROOT / "data" / "curated"

SCREENING_DIR = CURATED_DIR / "screening"
RANKING_DIR = CURATED_DIR / "ranking"
FULLTEXT_DIR = CURATED_DIR / "fulltext"

_screening = None
_screening_enriched = None
_ranking = None
_batches = None
_fulltext_decisions = None
_extractions = None
_artifacts = None
_quality_reviews = None


def _load_csv(dir, filename):
    path = dir / filename
    if path.exists():
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        return df
    return None


def load_all():
    global _screening, _screening_enriched, _ranking, _batches, _fulltext_decisions, _extractions, _artifacts, _quality_reviews
    _screening = _load_csv(SCREENING_DIR, "title_abstract_decisions.csv")
    _screening_enriched = _load_csv(SCREENING_DIR, "title_abstract_decisions_enriched.csv")
    _ranking = _load_csv(RANKING_DIR, "paper_priority_scores.csv")
    _batches = _load_csv(SCREENING_DIR, "screening_batches.csv")
    _fulltext_decisions = _load_csv(SCREENING_DIR, "full_text_decisions.csv")
    _extractions = _load_csv(FULLTEXT_DIR, "extraction_registry.csv")
    _artifacts = _load_csv(FULLTEXT_DIR, "artifact_registry.csv")
    _quality_reviews = _load_csv(FULLTEXT_DIR, "fulltext_quality_reviews.csv")


def screening():
    load_all()
    return _screening


def screening_enriched():
    load_all()
    return _screening_enriched


def ranking():
    load_all()
    return _ranking


def batches():
    load_all()
    return _batches


def extractions():
    load_all()
    return _extractions


def quality_reviews():
    load_all()
    return _quality_reviews


def paper_detail(rank):
    load_all()
    row = None
    if _screening_enriched is not None:
        row = _screening_enriched[_screening_enriched["rank"] == rank]
    elif _screening is not None:
        row = _screening[_screening["rank"] == rank]
    if row is None or row.empty:
        return None
    row = row.iloc[0].to_dict()

    for k, v in row.items():
        if isinstance(v, float) and pd.isna(v):
            row[k] = None

    candidate = row.get("candidate_id") or row.get("doi")

    if _ranking is not None and candidate:
        r = _ranking[_ranking["candidate_id"] == candidate]
        if not r.empty:
            row["priority"] = r.iloc[0].to_dict()

    if _extractions is not None:
        lookup = candidate
        e = _extractions[_extractions["candidate_id"] == lookup] if "candidate_id" in _extractions.columns else None
        if e is None or e.empty:
            e = _extractions[_extractions["paper_id"] == lookup] if "paper_id" in _extractions.columns else None
        if e is not None and not e.empty:
            row["extraction"] = e.iloc[0].to_dict()

    if _artifacts is not None and candidate:
        a = _artifacts[_artifacts["candidate_id"] == candidate] if "candidate_id" in _artifacts.columns else None
        if a is None or a.empty:
            a = _artifacts[_artifacts["paper_id"] == candidate] if "paper_id" in _artifacts.columns else None
        if a is not None and not a.empty:
            row["artifacts"] = a.to_dict(orient="records")

    return row
