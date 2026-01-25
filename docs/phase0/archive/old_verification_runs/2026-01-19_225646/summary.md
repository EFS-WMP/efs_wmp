# Phase 0 Verification Summary

| Field | Value |
|-------|-------|
| **Status** | FAIL |
| **Timestamp (UTC)** | 2026-01-20T06:56:46Z |
| **Commit SHA** | f053d6b |
| **Violations Found** | 48 |

## Artifacts

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

The following paths are excluded from scanning:
- docs/phase0/verification_runs/** â€” Run artifacts (self-reference prevention)
- docs/phase0/archive/** â€” Archived documents
- Binary files (pdf, png, jpg, jpeg, gif, zip, gz, 7z, tar)