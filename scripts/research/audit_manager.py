import argparse
import csv
import json
import random
import os
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(os.getenv("REPO_ROOT", "."))
CLAIM_LEDGER_PATH = REPO_ROOT / "data" / "curated" / "claim_ledger.csv"
AUDIT_LOG_PATH = REPO_ROOT / "data" / "curated" / "audit_log.csv"
MGA_MATRIX_PATH = REPO_ROOT / "outputs" / "method_gap_matrix.csv"
ARTIFACT_REGISTRY_PATH = REPO_ROOT / "data" / "curated" / "fulltext" / "artifact_registry.csv"

AUDIT_LOG_FIELDS = ["audit_id", "claim_id", "reviewer", "reviewed_at", "status", "sampled_pdfs", "notes"]

# Audit status -> claim-ledger status vocabulary (proposed/supported/contested/rejected/superseded)
LEDGER_STATUS_MAP = {
    "verified": "supported",
    "rejected": "rejected",
    "superseded": "superseded",
}


def _read_rows(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _atomic_write(path, rows, fieldnames):
    """Write rows to a temp file and atomically replace the target (commit point)."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def _new_audit_row(claim_id, reviewer, status, notes, sampled_pdfs):
    now = datetime.now(timezone.utc)
    return {
        "audit_id": "AUDIT_" + now.strftime("%Y%m%d%H%M%S%f"),
        "claim_id": claim_id,
        "reviewer": reviewer,
        "reviewed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "sampled_pdfs": " | ".join(sampled_pdfs) if sampled_pdfs else "",
        "notes": notes,
    }


def _append_audit_log(claim_id, reviewer, status, notes, sampled_pdfs):
    """Atomically append one row to audit_log.csv and return the audit row."""
    rows = _read_rows(AUDIT_LOG_PATH) if AUDIT_LOG_PATH.exists() else []
    audit_row = _new_audit_row(claim_id, reviewer, status, notes, sampled_pdfs)
    rows.append(audit_row)
    _atomic_write(AUDIT_LOG_PATH, rows, AUDIT_LOG_FIELDS)
    return audit_row

def get_pending():
    """Find the next proposed claim in the claim_ledger."""
    if not CLAIM_LEDGER_PATH.exists():
        print(json.dumps({"error": "claim_ledger.csv not found."}))
        return

    with open(CLAIM_LEDGER_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").strip().lower() == "proposed":
                print(json.dumps(row, indent=2))
                return
    print(json.dumps({"message": "No pending claims found."}))


def sample_evidence(claim_id, sample_size):
    """Sample N paper IDs and resolve their local PDF paths."""
    # 1. Read the claim to determine the evidence strategy
    claim = None
    if CLAIM_LEDGER_PATH.exists():
        with open(CLAIM_LEDGER_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["claim_id"] == claim_id:
                    claim = row
                    break
                    
    if not claim:
        print(json.dumps({"error": f"Claim {claim_id} not found in claim_ledger.csv."}))
        return

    evidence_ids_str = claim.get("evidence_ids", "").strip()
    sample = []
    message = None

    if evidence_ids_str == "method_gap_matrix.csv":
        # Random majority sample from the MGA matrix
        if not MGA_MATRIX_PATH.exists():
             print(json.dumps({"error": "method_gap_matrix.csv not found."}))
             return
        paper_ids = []
        with open(MGA_MATRIX_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_ids.append(row["paper_id"])
                
        if not paper_ids:
            print(json.dumps({"error": "No paper IDs found in MGA matrix."}))
            return
        sample = random.sample(paper_ids, min(sample_size, len(paper_ids)))
        message = f"Randomly sampled {len(sample)} papers from method_gap_matrix.csv"
        
    elif not evidence_ids_str or evidence_ids_str.endswith(".csv") or ".csv;" in evidence_ids_str:
        # Some dataset claims just point to dataset_opportunity_scores.csv without specific DOIs
        message = f"Claim points to generic files: {evidence_ids_str}. Manual review required."
        
    else:
        # Targeted anomaly or dataset claim with specific DOIs/IDs
        parts = evidence_ids_str.replace(";", ",").split(",")
        sample = [p.strip() for p in parts if p.strip()]
        # If there are many targeted IDs, we still sample N from them (or just return all if <= sample_size)
        sample = random.sample(sample, min(sample_size, len(sample)))
        message = f"Found {len(sample)} specific evidence IDs for targeted claim."

    # 2. Resolve to local PDF paths using artifact_registry
    results = []
    if sample:
        if ARTIFACT_REGISTRY_PATH.exists():
            with open(ARTIFACT_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                registry = list(reader)
                
            for pid in sample:
                found_pdf = None
                for row in registry:
                    if row["paper_id"] == pid and row.get("artifact_type") == "pdf" and row.get("stored_path"):
                        found_pdf = REPO_ROOT / row["stored_path"]
                        break
                results.append({
                    "paper_id": pid,
                    "pdf_path": str(found_pdf) if found_pdf else "Not found in registry"
                })
        else:
            for pid in sample:
                results.append({"paper_id": pid, "pdf_path": "Registry not found"})

    print(json.dumps({"claim_id": claim_id, "message": message, "samples": results}, indent=2))


def record_audit(claim_id, reviewer, status, notes, sampled_pdfs=None):
    """Append a verification record to the audit_log.csv (does not touch the ledger)."""
    audit_row = _append_audit_log(claim_id, reviewer, status, notes, sampled_pdfs or [])
    print(json.dumps({"status": "success", "message": f"Audit {audit_row['audit_id']} recorded for claim {claim_id}."}))


def mark_verified(claim_id, reviewer, status, notes, sampled_pdfs=None):
    """Record a human audit AND update the claim ledger row atomically.

    The ledger row status is mapped from the audit status into the claim-ledger
    vocabulary (verified->supported, rejected->rejected, superseded->superseded),
    so get-pending advances to the next proposed claim.
    """
    sampled_pdfs = sampled_pdfs or []
    if not CLAIM_LEDGER_PATH.exists():
        print(json.dumps({"error": "claim_ledger.csv not found."}))
        return

    rows = _read_rows(CLAIM_LEDGER_PATH)
    target = next((r for r in rows if r.get("claim_id") == claim_id), None)
    if target is None:
        print(json.dumps({"error": f"Claim {claim_id} not found in claim_ledger.csv."}))
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    ledger_status = LEDGER_STATUS_MAP.get(status)
    if ledger_status is None:
        print(json.dumps({"error": f"Invalid audit status '{status}'. Choose from {sorted(LEDGER_STATUS_MAP)}."}))
        return

    old_notes = (target.get("notes") or "").strip()
    target["status"] = ledger_status
    target["reviewer"] = reviewer
    target["reviewed_at"] = now
    audit_note = f"HUMAN AUDIT {status.upper()} by {reviewer} on {now}: {notes}"
    target["notes"] = f"{old_notes}; {audit_note}" if old_notes else audit_note

    audit_row = _new_audit_row(claim_id, reviewer, status, notes, sampled_pdfs)

    audit_rows = _read_rows(AUDIT_LOG_PATH) if AUDIT_LOG_PATH.exists() else []
    audit_rows.append(audit_row)
    _atomic_write(AUDIT_LOG_PATH, audit_rows, AUDIT_LOG_FIELDS)
    _atomic_write(CLAIM_LEDGER_PATH, rows, list(target.keys()))
    print(json.dumps({
        "status": "success",
        "message": f"Audit {audit_row['audit_id']} recorded and claim {claim_id} set to '{ledger_status}'.",
        "audit_id": audit_row["audit_id"],
        "claim_id": claim_id,
        "ledger_status": ledger_status,
        "reviewed_at": audit_row["reviewed_at"],
    }))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Human Validation Audit Manager")
    subparsers = parser.add_subparsers(dest="command")

    # Command: get-pending
    subparsers.add_parser("get-pending", help="Get the next pending claim.")

    # Command: sample-evidence
    parser_sample = subparsers.add_parser("sample-evidence", help="Sample N papers for a claim.")
    parser_sample.add_argument("--claim-id", required=True, help="The ID of the claim being audited.")
    parser_sample.add_argument("--sample-size", type=int, default=5, help="Number of papers to sample.")

    # Command: record-audit
    parser_record = subparsers.add_parser("record-audit", help="Append a verification record to audit_log.csv only.")
    parser_record.add_argument("--claim-id", required=True, help="The ID of the claim.")
    parser_record.add_argument("--reviewer", required=True, help="Name of the reviewer.")
    parser_record.add_argument("--status", required=True, choices=list(LEDGER_STATUS_MAP), help="Audit status.")
    parser_record.add_argument("--notes", required=True, help="Reviewer notes.")
    parser_record.add_argument("--pdfs", nargs="*", default=[], help="Sampled PDF paths inspected by the reviewer.")

    # Command: mark-verified
    parser_mark = subparsers.add_parser("mark-verified", help="Record a human audit AND update the claim ledger row atomically.")
    parser_mark.add_argument("--claim-id", required=True, help="The ID of the claim.")
    parser_mark.add_argument("--reviewer", required=True, help="Name of the reviewer.")
    parser_mark.add_argument("--status", required=True, choices=list(LEDGER_STATUS_MAP), help="Audit status (maps to ledger status).")
    parser_mark.add_argument("--notes", required=True, help="Reviewer notes.")
    parser_mark.add_argument("--pdfs", nargs="*", default=[], help="Sampled PDF paths inspected by the reviewer.")

    args = parser.parse_args()

    if args.command == "get-pending":
        get_pending()
    elif args.command == "sample-evidence":
        sample_evidence(args.claim_id, args.sample_size)
    elif args.command == "record-audit":
        record_audit(args.claim_id, args.reviewer, args.status, args.notes, args.pdfs)
    elif args.command == "mark-verified":
        mark_verified(args.claim_id, args.reviewer, args.status, args.notes, args.pdfs)
    else:
        parser.print_help()
