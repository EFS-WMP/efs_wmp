# Phase 0 Verification Summary

| Field | Value |
|-------|-------|
| **Status** | FAIL (TOOL ERROR) |
| **Timestamp (UTC)** | 2026-01-25T02:37:53Z |
| **Commit SHA** | b8a8707 |
| **Files Scanned** | 11 |
| **Violations Found** | 5 |

## Artifacts

- [scan_files.txt](./scan_files.txt) â€” List of files scanned
- [matches.txt](./matches.txt) â€” Violation details (by Rule ID)
- [env.json](./env.json) â€” Environment snapshot
- [commands.log](./commands.log) â€” Commands executed

## Rules Checked

### Forbidden Patterns (must NOT exist in docs/phase0)

| Rule ID | Description |
|---------|-------------|
| SOR_COMP_001 | Odoo is NOT the SoR for compliance; ITAD Core is |
| SOR_COMP_002 | Compliance data authority belongs to ITAD Core |
| SOR_COMP_003 | Compliance authority belongs to ITAD Core |
| SOR_ACC_001 | Acceptance commits to Odoo, not ITAD Core |
| SOR_ALL_001 | No single system owns ALL operational data |


### Required Patterns (must exist)

| Rule ID | File | Description |
|---------|------|-------------|
| REQ_SOR_ODOO_001 | docs/phase0/SOR_LOCK.md | SoR lock statement for Odoo |
| REQ_SOR_ITAD_001 | docs/phase0/SOR_LOCK.md | SoR lock statement for ITAD Core |


## Exclusions

The following paths are **completely excluded** from scanning:
- docs/phase0/verification_runs/** â€” Run artifacts (self-reference prevention)
- docs/phase0/archive/** â€” Archived documents and reference materials

Exclusions are enforced via explicit file list filtering. Files under these paths are never scanned.