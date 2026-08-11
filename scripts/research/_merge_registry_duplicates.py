import csv
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
REG = ROOT / "outputs" / "dataset_registry.csv"
SCORES = ROOT / "outputs" / "dataset_opportunity_scores.csv"
AUDIT = ROOT / "outputs" / "dataset_registry_dedup_audit.json"

CANONICAL = {
    "PLANesT-3D": "doi:10.48550/arxiv.2407.21150",
    "TomatoWUR": "doi:10.1016/j.dib.2025.111852",
}
MERGED_INTO = {
    "doi:10.1109/siu59756.2023.10223838": "doi:10.48550/arxiv.2407.21150",
    "doi:10.1016/j.biosystemseng.2025.104147": "doi:10.1016/j.dib.2025.111852",
}
NOTE_SUFFIX = {
    "doi:10.48550/arxiv.2407.21150": " [Also described in SIU 2023 conf paper doi:10.1109/siu59756.2023.10223838 (rank 237); metric-scale clouds 25-105 cm, >1M points, 21-105 leaves; CloudCompare labeling; compared vs Pheno4D/ROSE-X/Plant3D; download link in paper Sec I.]",
    "doi:10.1016/j.dib.2025.111852": " [Also used/described in doi:10.1016/j.biosystemseng.2025.104147 (rank 28, Marrewijk 2D-to-3D method study): split 35/4/5 plants with 525/60/75 RGB views; code github.com/WUR-ABE/2D-to-3D_segmentation; annotation ~1h/plant.]",
}

SCORE_FIELDS = [
    "paper_id", "dataset_name", "modality", "task", "data_richness", "underuse",
    "novelty_fit", "feasibility", "publication_leverage", "notes", "total", "rank",
]
DIMS = ("data_richness", "underuse", "novelty_fit", "feasibility", "publication_leverage")


def read_csv(p: Path):
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, rows, fieldnames):
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def f(x):
    return float(x) if x else 0.0


reg = read_csv(REG)
removed = []
kept = []
for r in reg:
    if r["paper_id"] in MERGED_INTO:
        removed.append(r)
    else:
        if r["paper_id"] in NOTE_SUFFIX and not r["notes"].endswith("]."):
            r["notes"] = (r["notes"] or "") + NOTE_SUFFIX[r["paper_id"]]
        kept.append(r)

scores = read_csv(SCORES)
rescore = read_csv(ROOT / "outputs" / "dataset_scoring_batch_rescore_staging.csv")

audit = {
    "policy": (
        "One registry/score row per dataset. Batch-8 extraction deduped by paper_id only, so "
        "dataset_name collisions (PLANesT-3D, TomatoWUR) were appended as separate rows; canonical "
        "row = introducing/data-descriptor paper, companion merged into notes. A first merge attempt "
        "keyed scores by dataset_name and wrongly collapsed 3 distinct 'not specified' datasets into "
        "one row (patrec.2015.10.013, dicta63115.2024.00095 absorbed into arxiv.2411.11285); the "
        "affected rows were re-scored from MGA evidence into dataset_scoring_batch_rescore_staging.csv "
        "and this merge keys ONLY by paper_id. All scores AI-provisional, human confirmation required."
    ),
    "merged_papers": {c: [p for p, cc in MERGED_INTO.items() if cc == c] for c in set(MERGED_INTO.values())},
    "rescored_papers": [r["paper_id"] for r in rescore],
    "removed_registry_rows": [r["paper_id"] for r in removed],
}

# ---- registry merge ----
write_csv(REG, kept, list(reg[0].keys()))
audit["registry_rows_after"] = len(kept)

# ---- scores rebuild: start from current scores (94), drop the 3 polluted 'not specified' rows,
#      add the 3 rescored rows, then merge per-dataset using only canonical paper_id keys ----
scores_by_pid = {r["paper_id"]: r for r in scores}

# 1) remove the 3 rows affected by the bad name-merge
for pid in ("doi:10.1016/j.patrec.2015.10.013", "doi:10.1109/dicta63115.2024.00095", "doi:10.48550/arxiv.2411.11285"):
    if pid in scores_by_pid:
        audit.setdefault("removed_polluted_score_rows", []).append(pid)
        del scores_by_pid[pid]

# 2) add rescored rows (keyed by paper_id)
for r in rescore:
    tot = sum(f(r[d]) for d in DIMS)
    scores_by_pid[r["paper_id"]] = {
        "paper_id": r["paper_id"],
        "dataset_name": r["dataset_name"],
        "modality": "",
        "task": "",
        "data_richness": r["data_richness"],
        "underuse": r["underuse"],
        "novelty_fit": r["novelty_fit"],
        "feasibility": r["feasibility"],
        "publication_leverage": r["publication_leverage"],
        "notes": r["notes"],
        "total": str(round(tot, 1)),
        "rank": "",
    }

# 3) drop any remaining rows for merged-away papers
for pid in MERGED_INTO:
    scores_by_pid.pop(pid, None)

# 4) re-rank deterministically (total desc, then paper_id asc for stability)
final = sorted(scores_by_pid.values(), key=lambda r: (-f(r["total"]), r["paper_id"]))
for i, r in enumerate(final, start=1):
    r["rank"] = str(i)

write_csv(SCORES, final, SCORE_FIELDS)
audit["score_rows_after"] = len(final)

with AUDIT.open("w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2, ensure_ascii=False)

print(f"registry: {len(reg)} -> {len(kept)} (removed {len(removed)})")
print(f"scores:   {len(scores)} -> {len(final)}")
print("top 12 after re-rank:")
for r in final[:12]:
    print(f"  {r['rank']:>2} {r['total']:>5} {r['dataset_name'][:45]}")
print("rescored placement:")
for pid in ("doi:10.1016/j.patrec.2015.10.013", "doi:10.1109/dicta63115.2024.00095", "doi:10.48550/arxiv.2411.11285"):
    r = scores_by_pid.get(pid, {})
    print(f"  rank {r.get('rank','?'):>3}  {r.get('total','?')}  {r.get('dataset_name','?')}")
print("audit:", AUDIT)
