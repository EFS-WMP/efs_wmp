# Phase 0 Verification Log

### PASS/FAIL Summary
- **Status:** PASS (pending final sign-off)
- **Notes:** Latest verification run recorded below; the SoR guard and evidence-index validator succeed and all Phase 0 items are PASS.

## How to run
1. `cd C:\odoo_dev`
2. `powershell -ExecutionPolicy Bypass -File scripts\phase0_verify.ps1`
   *This script executes the documented verification commands, stops on errors, and writes outputs to `docs/phase0/verification_runs/YYYY-MM-DD_HHMM.txt`.*

## Verification Run Record
| Date/Time | Runner | Git Commit | Environment | DB Migration Output | Test Output Summary | Seed Demo Output | SoR Greps Output |
|---|---|---|---|---|---|---|---|
| 2026-01-03 05:56 UTC | Codex SA | _not available (workspace lacks `.git`)_ | Windows PowerShell + Docker Compose (itad-core) | `docker compose -f docker-compose.itad-core.yml exec itad-core alembic upgrade head` (succeeds) | `docker compose -f docker-compose.itad-core.yml exec itad-core python -m pytest -q` (46 passed in 17.06s) | `docker compose -f docker-compose.itad-core.yml exec itad-core python -m app.scripts.seed_demo` (seed scenario with BOL/receiving + reconciliation + inventory/outbound/disposition flows) | SoR guard `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1` (PASS); `rg -n "\| (PARTIAL|FAIL) \|" docs/phase0/PHASE_0_EVIDENCE_INDEX.md` (no matches) |

> Additional runs can append new rows referencing the log files stored under `docs/phase0/verification_runs/`.

> Note: `python scripts/phase0_validate_evidence_index.py` produced “All referenced paths exist.”
