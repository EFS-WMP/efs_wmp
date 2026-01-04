param()
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $root
$files = @(
    "docs/phase0/PHASE_0.md",
    "docs/phase0/PHASE_0_LOCK_REVIEW.md",
    "docs/phase0/glossary.md",
    "docs/phase0/object_map.md",
    "docs/phase0/PHASE_0_EVIDENCE_INDEX.md",
    "docs/phase0/PHASE_0_VERIFICATION_LOG.md"
)
$files = $files | Where-Object { Test-Path $_ }
$forbiddenPatterns = @(
    "system of record for all operational data",
    "ITAD Core serves as the system of record for all operational data",
    "acceptance.*commits to ITAD Core"
)
$lockStatement = "Odoo is the system of record for Scheduling, Day Routes, and Dispatch execution."
$hasLock = Select-String -Pattern "Acceptance/dispatch execution commits to Odoo" -Path "docs/phase0/PHASE_0.md" -Quiet
$hasLockArtifacts = Select-String -Pattern "ITAD Core receives compliance artifacts later via pickup_manifest" -Path "docs/phase0/PHASE_0.md" -Quiet
$lockPresent = $hasLock -and $hasLockArtifacts
$failures = @()
if (-not $lockPresent) {
    $failures += "SoR lock statement missing in docs/phase0/PHASE_0.md"
}
foreach ($file in $files) {
    if ($file -like "docs/phase0/archive/*") { continue }
    foreach ($pattern in $forbiddenPatterns) {
        $match = Select-String -Pattern $pattern -Path $file -CaseSensitive:$false
        if ($match) {
            $failures += "`"$pattern`" found in $file"
        }
    }
}
if ($failures.Count -gt 0) {
    "SOR Guardrail Status: FAIL" 
    $failures | ForEach-Object { " - $_" }
    exit 1
}
"SOR Guardrail Status: PASS"
exit 0
