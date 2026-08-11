from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/fulltext_pipeline/src"))

from agri_fulltext.acquisition import import_local_artifact
from agri_fulltext.config import load_settings
from agri_fulltext.queueing import load_eligible_works

plan = json.loads((REPO / "outputs/manual_pdf_import_plan_20260803.json").read_text(encoding="utf-8"))
imports = [p for p in plan if p["action"] == "IMPORT"]

settings = load_settings(REPO)
works = {w.paper_id: w for w in load_eligible_works(settings)}
downloads = Path(r"C:\Users\mouadh\Downloads")
files = {f.name: f for f in downloads.iterdir() if f.is_file()}

results = []
errors = []
for i, p in enumerate(imports, 1):
    fpath = files[p["file"]]
    work = works[p["matched_paper_id"]]
    note = f"user-supplied PDF; {p.get('note', '')}"[:400]
    try:
        row = import_local_artifact(
            settings,
            work,
            fpath,
            rights_status="local_research_only",
            license_value="",
            version="user_supplied",
            notes=note,
        )
        results.append({"index": i, "file": p["file"], "paper_id": work.paper_id, "rank": work.rank, "artifact_id": row["artifact_id"], "sha256": row["sha256"]})
        print(f"[{i:02d}/{len(imports)}] OK   {row['artifact_id']}  r{work.rank:<5} {p['file'][:58]}")
    except Exception as exc:  # noqa: BLE001
        errors.append({"file": p["file"], "paper_id": work.paper_id, "rank": work.rank, "error": str(exc)})
        print(f"[{i:02d}/{len(imports)}] FAIL {p['file'][:58]}  {str(exc)[:120]}")

report = {"total": len(imports), "imported": len(results), "failed": len(errors), "results": results, "errors": errors}
(REPO / "outputs/manual_pdf_import_report_20260803.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print()
print("IMPORTED", len(results), "/", len(imports))
if errors:
    print("ERRORS", len(errors))
    for e in errors:
        print("  ", e["file"][:60], "->", e["error"][:150])
