---
name: human-validation-audit
description: Guides the user through a step-by-step human validation audit of AI-extracted claims in the claim_ledger.csv.
---

# Human Validation Audit Skill

This skill turns the agent into an interactive "Audit Guide." The agent handles the tedious work of finding claims, looking up evidence, sampling papers, and updating the ledger.

## Trigger
Use this skill when the user runs the `/audit-claim` command or asks to audit/verify the claims.

## Workflow

1. **Find Next Pending Claim:** 
   Run the helper script: `python scripts/research/audit_manager.py get-pending`.
   If there are no pending claims, inform the user and stop.
   If there is a claim, read its details (claim text, scope, evidence location).

2. **Present the Claim:**
   Show the user the claim ID, the claim text, and what evidence supports it.
   Determine what kind of audit is needed based on the claim type:
   - **Targeted Anomaly:** (e.g., specific papers are mentioned in the `evidence_locations` column).
   - **Random Majority Sample:** (e.g., "189 papers lack calibration").
   - **Dataset Finalist:** (e.g., dataset opportunity rankings).

3. **Fetch Evidence:**
   Use the helper script to get the PDF path(s) to read.
   Run: `python scripts/research/audit_manager.py sample-evidence --claim-id <ID> --sample-size <N>` (N=5 for majority claims; N=1 for specific anomaly claims if applicable).
   Present the local PDF path(s) using markdown links to the user.
   Keep the returned PDF paths; you will pass them to `mark-verified` so the audit log records exactly which documents were inspected.

4. **Ask the Verification Question:**
   Ask the user what they need to verify based on the claim.
   *Example: "Please open this PDF and check if there is any mention of calibration or ECE. Do you confirm the AI's assessment?"*

5. **Wait for User Response:**
   Stop executing and wait for the user to read the PDF and reply.

6. **Record the Audit:**
   After the user replies, run the helper script to record the audit into `audit_log.csv` AND update the claim ledger row (status maps to `supported`/`rejected`/`superseded`, so `get-pending` advances):
   `python scripts/research/audit_manager.py mark-verified --claim-id <ID> --reviewer "USER" --status <verified/rejected/superseded> --notes "<Summary of user response>" --pdfs <sampled pdf path 1> <sampled pdf path 2> ...`
   Inform the user that the audit has been recorded in `data/curated/audit_log.csv` and the claim status updated in `data/curated/claim_ledger.csv`.
   Note: use `record-audit` only when you want an audit-log entry without touching the ledger.

7. **Ask to Continue:**
   Ask the user if they want to audit the next pending claim. If yes, loop back to Step 1.
