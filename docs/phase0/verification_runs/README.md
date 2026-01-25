# Phase 0 Verification Runs

This directory contains timestamped verification run artifacts. Each run validates that System-of-Record (SoR) boundaries are correctly documented and enforced.

## Directory Structure

```
verification_runs/
├── 2026-01-24_183908/          # Latest PASS run
│   ├── summary.md              # PASS/FAIL summary with metadata
│   ├── matches.txt             # Violation details (Rule IDs only)
│   ├── env.json                # Environment snapshot
│   ├── commands.log            # Commands executed
│   └── scan_files.txt          # List of files scanned
└── README.md                   # This file
```

## Artifact Retention Policy

### Active Runs (This Directory)

- **Keep**: Last 5-10 successful PASS runs
- **Format**: Folder-based runs only (`YYYY-MM-DD_HHMMSS/`)
- **Content**: Rule IDs only, never raw forbidden patterns

### Archived Runs

- **Location**: `../archive/old_verification_runs/`
- **Content**: Legacy `.txt` runs and old folders that may contain raw forbidden patterns
- **Exclusion**: Automatically excluded from verification scanning via `archive/**` pattern

### Cleanup Procedure

When this directory has more than 10 runs:

```powershell
# Move runs older than 30 days to archive
cd c:\odoo_dev\docs\phase0\verification_runs
$cutoffDate = (Get-Date).AddDays(-30)
Get-ChildItem -Directory | Where-Object { 
    $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{6}$' -and 
    [DateTime]::ParseExact($_.Name.Substring(0,10), 'yyyy-MM-dd', $null) -lt $cutoffDate
} | Move-Item -Destination ..\archive\old_verification_runs\
```

## Running Verification

```powershell
cd c:\odoo_dev
powershell -ExecutionPolicy Bypass -File scripts\phase0_verify.ps1
```

**Expected Output**:
- PASS: No forbidden patterns found, all required patterns present
- FAIL: Violations detected or required patterns missing

## Artifact Contents

### summary.md

High-level PASS/FAIL status with:
- Timestamp (UTC)
- Commit SHA
- Files scanned count
- Violations count
- Rules checked (Rule IDs and descriptions only)

**Critical**: Never contains raw forbidden patterns, only Rule IDs.

### matches.txt

Violation details:
- If PASS: "No violations found."
- If FAIL: List of violations with Rule IDs and file locations

**Critical**: No `archive\` or `verification_runs\` paths should appear (AC-A2).

### env.json

Environment snapshot for reproducibility:
- Timestamp (UTC and local)
- User and computer name
- OS and PowerShell version
- Ripgrep version
- Working directory
- Commit SHA

### commands.log

Commands executed during verification:
- File discovery command
- Rule checks (with redacted patterns)
- Required pattern checks

### scan_files.txt

List of files scanned (one per line):
- Forward slash paths for ripgrep compatibility
- Excludes `archive/**` and `verification_runs/**`

## Maintenance

- **Frequency**: Run before each commit to `docs/phase0/**`
- **Cleanup**: Monthly (move old runs to archive)
- **Monitoring**: Weekly automated check (see CI gate)

## CI Integration

Automated verification runs on:
- Pull requests touching `docs/phase0/**` or `scripts/phase0_verify.ps1`
- Pushes to main branch

See `.github/workflows/phase0-verification.yml` for configuration.

## Troubleshooting

**Issue**: Verification fails with old runs causing violations

**Fix**: Move old runs to archive:
```powershell
Move-Item verification_runs\<old-run> ..\archive\old_verification_runs\
```

**Issue**: "TOOL ERROR (rg exit 2)"

**Fix**: Ensure ripgrep is installed:
```powershell
rg --version
# If not found: choco install ripgrep -y
```

## References

- [PHASE_0_VERIFICATION_LOG.md](../PHASE_0_VERIFICATION_LOG.md) - Complete verification history
- [PHASE_0A_SUSTAINABILITY.md](../PHASE_0A_SUSTAINABILITY.md) - Detailed maintenance guide
- [phase0_verify.ps1](../../scripts/phase0_verify.ps1) - Verification script
