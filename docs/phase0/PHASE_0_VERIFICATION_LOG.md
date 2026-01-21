# Phase 0 Verification Log (Index)

This document serves as an **index of verification runs**, not a rewritten narrative. Each run entry links to timestamped artifacts containing full logs and match details.

## How to Run

```powershell
cd C:\odoo_dev
powershell -ExecutionPolicy Bypass -File scripts\phase0_verify.ps1
```

The script will:
1. Scan `docs/phase0` for forbidden SoR patterns (excluding `verification_runs/**` and binaries)
2. Check for required SoR lock statements
3. Create a timestamped run folder under `docs/phase0/verification_runs/<timestamp>/`
4. Generate `raw.log`, `matches.txt`, and `summary.md` artifacts
5. Exit with code 0 (PASS) or 1 (FAIL)

## Run Index

| UTC Timestamp | Commit SHA | Environment | Command | Result | Artifacts |
|---------------|------------|-------------|---------|--------|-----------|
| 2026-01-03T05:56:00Z | N/A | Windows PowerShell + Docker | `scripts/phase0_verify.ps1` | PASS | [2026-01-02_2112.txt](./verification_runs/2026-01-02_2112.txt) (legacy format) |

> [!NOTE]
> Legacy runs (before 2026-01-20) used a flat text file format. New runs create a folder with structured artifacts.

## Run Artifact Structure

Each new run creates a folder: `docs/phase0/verification_runs/<YYYY-MM-DD_HHMMSS>/`

| File | Description |
|------|-------------|
| `raw.log` | Full stdout/stderr from the verification run |
| `matches.txt` | List of forbidden pattern matches (or "No forbidden patterns found") |
| `summary.md` | PASS/FAIL summary with metadata (commit SHA, timestamp, violation count) |

## Adding New Run Entries

After running the verification script:

1. Note the run folder path printed to console
2. Add a new row to the Run Index table above with:
   - UTC Timestamp (from `summary.md`)
   - Commit SHA (from `summary.md` or `git rev-parse --short HEAD`)
   - Environment (e.g., `dev/Windows PowerShell`, `CI/GitHub Actions`)
   - Command executed
   - Result (PASS/FAIL)
   - Link to the run artifacts folder
