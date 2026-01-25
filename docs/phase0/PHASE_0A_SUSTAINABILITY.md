# Phase 0A Sustainability & Maintenance Guide

## Purpose

This document outlines policies and procedures to prevent Phase 0A gate from breaking due to self-referential verification artifacts or forbidden pattern leakage.

## Artifact Retention Policy

### Current State (Post-Cleanup)

✅ **Active Runs**: `docs/phase0/verification_runs/`
- Keep only folder-based runs (format: `YYYY-MM-DD_HHMMSS/`)
- Each run contains: `summary.md`, `matches.txt`, `env.json`, `commands.log`, `scan_files.txt`
- **Critical**: All artifacts use Rule IDs only, never raw forbidden patterns

✅ **Archived Runs**: `docs/phase0/archive/old_verification_runs/`
- Legacy `.txt` format runs (e.g., `2026-01-02_2112.txt`)
- Old folder-based runs that may contain raw forbidden patterns
- Automatically excluded from verification scanning via `archive/**` exclusion

### Retention Rules

1. **Keep Last 5 Successful Runs**: Maintain the 5 most recent PASS runs in `verification_runs/`
2. **Archive Older Runs**: Move runs older than 30 days to `archive/old_verification_runs/`
3. **Delete Ancient Archives**: Remove archived runs older than 90 days (optional, for space management)

### Manual Cleanup Procedure

When `verification_runs/` has more than 10 folders:

```powershell
# Run from c:\odoo_dev
cd docs\phase0\verification_runs

# List all runs sorted by date
Get-ChildItem -Directory | Sort-Object Name

# Move old runs to archive (example: runs older than 30 days)
$cutoffDate = (Get-Date).AddDays(-30)
Get-ChildItem -Directory | Where-Object { 
    $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{6}$' -and 
    [DateTime]::ParseExact($_.Name.Substring(0,10), 'yyyy-MM-dd', $null) -lt $cutoffDate
} | Move-Item -Destination ..\archive\old_verification_runs\
```

## Forbidden Pattern Prevention

### Rule: Never Write Raw Forbidden Strings

**Prohibited Locations**:
- `docs/phase0/**/*.md` (except `archive/**`)
- Verification run artifacts (`summary.md`, `matches.txt`, `commands.log`)
- `PHASE_0_VERIFICATION_LOG.md`

**Allowed Locations**:
- `docs/phase0/archive/forbidden_examples_reference.md` (explicitly excluded)
- Script source code (`scripts/phase0_verify.ps1` - pattern definitions only)

### Safe Documentation Practices

✅ **DO**:
- Use Rule IDs: `SOR_COMP_001`, `SOR_ACC_001`, etc.
- Use neutral descriptions: "Odoo is NOT the SoR for compliance"
- Reference patterns indirectly: "See rule definition in verification script"

❌ **DON'T**:
- Write forbidden strings verbatim in docs
- Copy-paste violation examples into documentation
- Include raw patterns in verification logs

### Example: Safe vs. Unsafe

```markdown
<!-- ❌ UNSAFE - Will trigger verification failure -->
The pattern "Odoo is the system of record for compliance" is forbidden.

<!-- ✅ SAFE - Uses Rule ID -->
Rule SOR_COMP_001 prohibits claiming Odoo as the SoR for compliance.
```

## CI Gate Configuration

### GitHub Actions Workflow

Create `.github/workflows/phase0-verification.yml`:

```yaml
name: Phase 0 SoR Verification

on:
  pull_request:
    paths:
      - 'docs/phase0/**'
      - 'scripts/phase0_verify.ps1'
  push:
    branches:
      - main
    paths:
      - 'docs/phase0/**'

jobs:
  verify:
    runs-on: windows-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Install ripgrep
        run: choco install ripgrep -y
      
      - name: Run Phase 0 Verification
        run: |
          cd ${{ github.workspace }}
          powershell -ExecutionPolicy Bypass -File scripts\phase0_verify.ps1
        shell: pwsh
      
      - name: Upload verification artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: phase0-verification-results
          path: docs/phase0/verification_runs/
          retention-days: 30
      
      - name: Fail on violations
        if: failure()
        run: |
          Write-Host "❌ Phase 0 verification failed. Check artifacts for details." -ForegroundColor Red
          exit 1
```

### Alternative: Generic CI (GitLab, Jenkins, etc.)

```bash
#!/bin/bash
# ci-phase0-verify.sh

set -e

echo "Installing ripgrep..."
# Adjust for your CI environment
apt-get update && apt-get install -y ripgrep

echo "Running Phase 0 verification..."
cd /path/to/repo
pwsh -File scripts/phase0_verify.ps1

if [ $? -ne 0 ]; then
  echo "❌ Phase 0 verification failed"
  exit 1
fi

echo "✅ Phase 0 verification passed"
```

## Monitoring & Alerts

### Weekly Verification Check

Schedule a weekly verification run to catch drift:

```powershell
# Add to scheduled task or cron
# Run every Monday at 9 AM
powershell -ExecutionPolicy Bypass -File c:\odoo_dev\scripts\phase0_verify.ps1

# Optional: Send email notification on failure
if ($LASTEXITCODE -ne 0) {
    Send-MailMessage -To "team@example.com" `
        -Subject "⚠️ Phase 0 Verification Failed" `
        -Body "Weekly verification check failed. Review required." `
        -SmtpServer "smtp.example.com"
}
```

### Metrics to Track

- Verification run frequency
- PASS/FAIL rate over time
- Number of violations per run
- Time to resolve failures

## Change Control Process

### Before Modifying docs/phase0/**

1. **Run verification locally**: Ensure current state is PASS
2. **Make changes**: Edit documentation
3. **Run verification again**: Confirm still PASS
4. **Review changes**: Check for accidental forbidden patterns
5. **Submit PR**: CI gate will verify automatically
6. **Merge only if PASS**: Do not merge failing PRs

### Emergency Fixes

If verification fails on main branch:

1. **Identify violation**: Check latest run in `verification_runs/`
2. **Fix immediately**: Remove forbidden patterns or fix exclusions
3. **Verify fix**: Run `scripts\phase0_verify.ps1` locally
4. **Fast-track PR**: Bypass normal review if critical
5. **Document incident**: Add note to `PHASE_0_VERIFICATION_LOG.md`

## Troubleshooting Common Issues

### Issue: Verification fails with "TOOL ERROR"

**Cause**: Ripgrep not installed or incompatible version

**Fix**:
```powershell
# Check ripgrep version
rg --version

# Reinstall if needed (Windows)
choco install ripgrep -y

# Or download from: https://github.com/BurntSushi/ripgrep/releases
```

### Issue: Old runs causing violations

**Cause**: Legacy artifacts contain raw forbidden patterns

**Fix**:
```powershell
# Move to archive
Move-Item docs\phase0\verification_runs\<old-run> `
          docs\phase0\archive\old_verification_runs\
```

### Issue: New forbidden pattern added but not detected

**Cause**: Pattern not added to `$forbiddenPatterns` array in script

**Fix**: Update `scripts/phase0_verify.ps1` lines 97-123 with new rule

## Best Practices Summary

1. ✅ **Use Rule IDs everywhere** - Never write raw forbidden strings in docs
2. ✅ **Archive old runs regularly** - Keep `verification_runs/` clean
3. ✅ **Run verification before commits** - Catch issues early
4. ✅ **Enable CI gate** - Prevent forbidden patterns from merging
5. ✅ **Monitor weekly** - Automated checks catch drift
6. ✅ **Document changes** - Update `PHASE_0_VERIFICATION_LOG.md` for each run

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Run verification locally | Before each commit | Developer |
| Archive old runs | Monthly | Engineering TL |
| Review verification log | Quarterly | Solution Architect |
| Update forbidden patterns | As needed | Compliance |
| CI gate health check | Weekly | DevOps |

## References

- [PHASE_0_VERIFICATION_LOG.md](../PHASE_0_VERIFICATION_LOG.md) - Verification run history
- [PHASE_0A_SIGNOFF.md](../PHASE_0A_SIGNOFF.md) - Gate sign-off documentation
- [phase0_verify.ps1](../../scripts/phase0_verify.ps1) - Verification script
- [forbidden_examples_reference.md](../archive/forbidden_examples_reference.md) - Forbidden pattern examples (archived)
