$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootDir = Split-Path -Parent $scriptDir
Set-Location -Path $rootDir
$logDir = "docs/phase0/verification_runs"
If (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$logFile = Join-Path $logDir "$timestamp.txt"
"Phase 0 verification run - $timestamp" | Out-File $logFile
"----------------------------------------" | Out-File $logFile -Append

$commands = @(
    'rg -n "system of record for all operational data" docs/phase0',
    'rg -n "ITAD Core serves as the system of record" docs/phase0',
    'rg -n "acceptance.*commits to ITAD Core" docs/phase0',
    'rg -n "PHASE_0\.md|PHASE_0_LOCK_REVIEW\.md|glossary\.md|object_map\.md" -S docs/phase0',
    'rg -n "Phase 0 Verification Log" docs/phase0/PHASE_0_VERIFICATION_LOG.md',
    'python scripts/phase0_validate_evidence_index.py'
)

foreach ($cmd in $commands) {
    "Running: $cmd" | Out-File $logFile -Append
    $result = Invoke-Expression "$cmd" 2>&1
    $result | Out-File $logFile -Append
    if ($LASTEXITCODE -ne 0) {
        "Command failed: $cmd" | Out-File $logFile -Append
        throw "Verification command failed: $cmd"
    }
}

"All commands succeeded." | Out-File $logFile -Append
"Log saved to $logFile" | Out-File $logFile -Append
