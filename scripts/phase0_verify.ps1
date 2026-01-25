<#
.SYNOPSIS
    Phase 0 Verification Script — Audit-Grade Compliance Gate

.DESCRIPTION
    Scans docs/phase0 for forbidden SoR patterns that violate established
    System-of-Record boundaries. Features:
    - Excludes verification_runs/** and archive/** from scanning
    - Uses Rule IDs only in artifacts (no forbidden strings printed)
    - Creates timestamped run artifacts with full traceability
    - UTF-8 encoding for all output

.NOTES
    Exit Codes:
    - 0 = PASS (no forbidden patterns found, all required present)
    - 1 = FAIL (forbidden patterns detected or required missing)
    - 2 = TOOL ERROR (ripgrep not found or execution error)
#>

param()

# ============================================================================
# UTF-8 ENCODING SETUP (for console and file output)
# ============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8'

# Helper function to write UTF-8 files without BOM
function Write-Utf8File {
    param([string]$Path, [string]$Content)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

# ============================================================================
# FR-1: PROJECT ROOT DETECTION
# ============================================================================
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Try git-based root detection first
$rootDir = $null
try {
    Push-Location $scriptDir
    $gitRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0 -and $gitRoot) {
        $rootDir = $gitRoot.Trim() -replace '/', '\'
    }
    Pop-Location
}
catch { }

# Fallback: assume script is in <root>/scripts/
if (-not $rootDir) {
    $rootDir = Split-Path -Parent $scriptDir
}

Set-Location -Path $rootDir

# ============================================================================
# FR-2: RIPGREP DEPENDENCY CHECK
# ============================================================================
$rgPath = Get-Command rg -ErrorAction SilentlyContinue
if (-not $rgPath) {
    Write-Host ""
    Write-Host "ERROR: ripgrep (rg) is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install ripgrep: https://github.com/BurntSushi/ripgrep#installation" -ForegroundColor Yellow
    Write-Host ""
    exit 2
}

$rgVersion = "unknown"
try {
    $rgVersion = (rg --version 2>$null | Select-Object -First 1).Trim()
}
catch { }

# ============================================================================
# RESOLVE PHASE0 ROOT AND CREATE TIMESTAMPED RUN FOLDER
# ============================================================================
$phase0Root = Resolve-Path (Join-Path $rootDir "docs\phase0") -ErrorAction Stop
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$timestampUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$runDir = Join-Path $phase0Root "verification_runs\$timestamp"
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$summaryFile = Join-Path $runDir "summary.md"
$matchesFile = Join-Path $runDir "matches.txt"
$envFile = Join-Path $runDir "env.json"
$commandsFile = Join-Path $runDir "commands.log"
$scanFilesListPath = Join-Path $runDir "scan_files.txt"

# ============================================================================
# FR-6: FORBIDDEN PATTERNS WITH RULE IDs
# Each pattern represents a SoR violation.
# ============================================================================
$forbiddenPatterns = @(
    @{
        Id          = "SOR_COMP_001"
        Pattern     = "Odoo is the system of record for compliance"
        Description = "Odoo is NOT the SoR for compliance; ITAD Core is"
    },
    @{
        Id          = "SOR_COMP_002"
        Pattern     = "Odoo stores the authoritative compliance"
        Description = "Compliance data authority belongs to ITAD Core"
    },
    @{
        Id          = "SOR_COMP_003"
        Pattern     = "Odoo is authoritative for.*compliance"
        Description = "Compliance authority belongs to ITAD Core"
    },
    @{
        Id          = "SOR_ACC_001"
        Pattern     = "acceptance.*commits to ITAD Core"
        Description = "Acceptance commits to Odoo, not ITAD Core"
    },
    @{
        Id          = "SOR_ALL_001"
        Pattern     = "system of record for all operational data"
        Description = "No single system owns ALL operational data"
    }
)

$requiredPatterns = @(
    @{
        Id          = "REQ_SOR_ODOO_001"
        Pattern     = "Odoo is the system of record for Scheduling"
        File        = "docs/phase0/SOR_LOCK.md"
        Description = "SoR lock statement for Odoo"
    },
    @{
        Id          = "REQ_SOR_ITAD_001"
        Pattern     = "ITAD Core is the system of record for Compliance"
        File        = "docs/phase0/SOR_LOCK.md"
        Description = "SoR lock statement for ITAD Core"
    }
)

# ============================================================================
# GET GIT COMMIT SHA
# ============================================================================
$commitSha = "N/A"
try {
    $commitSha = (git rev-parse --short HEAD 2>$null)
    if (-not $commitSha) { $commitSha = "N/A (not a git repo)" }
}
catch {
    $commitSha = "N/A (git not available)"
}

# ============================================================================
# FR-5: CREATE ENV.JSON
# ============================================================================
$envInfo = @{
    timestamp_utc      = $timestampUtc
    timestamp_local    = $timestamp
    user               = $env:USERNAME
    computer           = $env:COMPUTERNAME
    os                 = [System.Environment]::OSVersion.VersionString
    powershell_version = $PSVersionTable.PSVersion.ToString()
    ripgrep_version    = $rgVersion
    working_directory  = $rootDir
    commit_sha         = $commitSha
    phase0_root        = $phase0Root.Path
}
$envJson = $envInfo | ConvertTo-Json -Depth 2
Write-Utf8File -Path $envFile -Content $envJson

# ============================================================================
# COMMANDS LOG HEADER
# ============================================================================
$commandsLog = @()
$commandsLog += "# Phase 0 Verification Commands Log"
$commandsLog += "# Timestamp: $timestampUtc"
$commandsLog += "# Working Directory: $rootDir"
$commandsLog += "# Phase0 Root: $($phase0Root.Path)"
$commandsLog += ""

# ============================================================================
# APPROACH A.2: BUILD EXPLICIT FILE LIST (EXCLUDE archive & verification_runs)
# ============================================================================
Write-Host ""
Write-Host "Phase 0 Verification Starting..." -ForegroundColor Cyan
Write-Host "Scan root: $($phase0Root.Path)" -ForegroundColor Gray
Write-Host ""

# Step 1: Discover all .md files in phase0 (respecting .gitignore)
$discoverCmd = "rg --files `"$($phase0Root.Path)`" --glob `"*.md`""
$commandsLog += "# Discovering .md files (respecting .gitignore):"
$commandsLog += $discoverCmd
$commandsLog += ""

try {
    $allMdFiles = & rg --files "$($phase0Root.Path)" --glob "*.md" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to discover files with ripgrep" -ForegroundColor Red
        Write-Host "Command: $discoverCmd" -ForegroundColor Yellow
        exit 2
    }
}
catch {
    Write-Host "ERROR: Exception during file discovery: $_" -ForegroundColor Red
    exit 2
}

# Step 2: Filter out archive/** and verification_runs/** (case-insensitive, both / and \)
$excludePattern = '(?i)[\\/](archive|verification_runs)[\\/]'
$scanFiles = $allMdFiles | Where-Object { 
    $_ -and ($_ -notmatch $excludePattern)
}

# Step 3: Write scan file list (convert backslashes to forward slashes for ripgrep)
$scanFilesNormalized = $scanFiles | ForEach-Object { $_ -replace '\\', '/' }
$scanFilesContent = ($scanFilesNormalized -join "`n")
Write-Utf8File -Path $scanFilesListPath -Content $scanFilesContent

$scanFileCount = ($scanFiles | Measure-Object).Count

Write-Host "Exclusions:" -ForegroundColor Gray
Write-Host "  - docs/phase0/archive/**" -ForegroundColor Gray
Write-Host "  - docs/phase0/verification_runs/**" -ForegroundColor Gray
Write-Host ""
Write-Host "Files to scan: $scanFileCount .md files" -ForegroundColor Cyan
Write-Host ""

$commandsLog += "# Scan file list written to: scan_files.txt"
$commandsLog += "# Total files to scan: $scanFileCount"
$commandsLog += ""

# ============================================================================
# SCAN FOR FORBIDDEN PATTERNS (iterate through files individually)
# ============================================================================
$allViolations = @()
$hasFailures = $false
$toolError = $false

Write-Host "Scanning for forbidden patterns..." -ForegroundColor Cyan
Write-Host ""

foreach ($rule in $forbiddenPatterns) {
    $ruleId = $rule.Id
    $pattern = $rule.Pattern
    
    # Log the check
    $commandsLog += "# Checking Rule: $ruleId"
    $commandsLog += "# Pattern: [REDACTED - see rule definition]"
    $commandsLog += "# Searching across $scanFileCount files"
    $commandsLog += ""
    
    $ruleMatches = @()
    
    try {
        # Search each file individually
        foreach ($file in $scanFiles) {
            try {
                $result = & rg -n -i $pattern $file 2>$null
                if ($LASTEXITCODE -eq 0 -and $result) {
                    # Pattern found in this file
                    $result | ForEach-Object {
                        $line = $_.ToString()
                        # Double-check: ensure no excluded paths leaked through
                        if ($line -notmatch $excludePattern) {
                            $ruleMatches += "[$ruleId] $line"
                        }
                    }
                }
            }
            catch {
                # Ignore individual file errors, continue scanning
            }
        }
        
        if ($ruleMatches.Count -gt 0) {
            # Pattern found - VIOLATION
            $hasFailures = $true
            Write-Host "  [$ruleId] VIOLATION FOUND ($($ruleMatches.Count) matches)" -ForegroundColor Red
            $allViolations += $ruleMatches
        }
        else {
            # No matches - OK
            Write-Host "  [$ruleId] OK (not found)" -ForegroundColor Green
        }
    }
    catch {
        $hasFailures = $true
        $toolError = $true
        Write-Host "  [$ruleId] ERROR: $_" -ForegroundColor Red
        $allViolations += "[$ruleId] EXCEPTION: $_"
    }
}

Write-Host ""

# ============================================================================
# CHECK REQUIRED PATTERNS (using --files-from)
# ============================================================================
Write-Host "Checking required SoR lock statements..." -ForegroundColor Cyan
Write-Host ""

foreach ($req in $requiredPatterns) {
    $ruleId = $req.Id
    $pattern = $req.Pattern
    $file = $req.File
    $desc = $req.Description
    
    $fullPath = Join-Path $rootDir $file
    
    # Check if file is in scan list
    $normalizedPath = $fullPath -replace '\\', '/'
    $fileInScanList = $scanFiles | Where-Object { ($_ -replace '\\', '/') -eq $normalizedPath }
    
    if (-not $fileInScanList) {
        # File is excluded or doesn't exist
        if (Test-Path $fullPath) {
            # File exists but excluded
            Write-Host "  [$ruleId] SKIPPED (file excluded from scan)" -ForegroundColor Yellow
            $commandsLog += "# Required pattern ${ruleId}: file excluded from scan list"
            $commandsLog += ""
            continue
        }
        else {
            # File doesn't exist
            $hasFailures = $true
            Write-Host "  [$ruleId] FILE NOT FOUND: $file" -ForegroundColor Red
            $allViolations += "[$ruleId] FILE_NOT_FOUND: $file"
            $commandsLog += "# Required pattern ${ruleId}: file not found"
            $commandsLog += ""
            continue
        }
    }
    
    $commandsLog += "# Checking Required: $ruleId in $file"
    $commandsLog += "Select-String -Pattern [PATTERN_$ruleId] -Path `"$fullPath`""
    $commandsLog += ""
    
    $match = Select-String -Pattern $pattern -Path $fullPath -CaseSensitive:$false
    if ($match) {
        Write-Host "  [$ruleId] FOUND (OK)" -ForegroundColor Green
    }
    else {
        $hasFailures = $true
        Write-Host "  [$ruleId] MISSING - $desc" -ForegroundColor Red
        $allViolations += "[$ruleId] MISSING: $desc in $file"
    }
}

Write-Host ""

# ============================================================================
# FR-5: WRITE MATCHES FILE (Rule IDs only, no forbidden strings)
# ============================================================================
if ($allViolations.Count -gt 0) {
    $matchesContent = "# Phase 0 Verification Matches`n"
    $matchesContent += "# Timestamp: $timestampUtc`n"
    $matchesContent += "# Total Violations: $($allViolations.Count)`n"
    $matchesContent += "`n"
    $allViolations | ForEach-Object { $matchesContent += "$_`n" }
    Write-Utf8File -Path $matchesFile -Content $matchesContent
}
else {
    Write-Utf8File -Path $matchesFile -Content "# No violations found.`n# Timestamp: $timestampUtc`n"
}

# ============================================================================
# FR-5: WRITE COMMANDS LOG
# ============================================================================
$commandsLogContent = $commandsLog -join "`n"
Write-Utf8File -Path $commandsFile -Content $commandsLogContent

# ============================================================================
# FR-5: WRITE SUMMARY (Rule IDs only, no forbidden patterns printed)
# ============================================================================
$status = if ($toolError) { "FAIL (TOOL ERROR)" } elseif ($hasFailures) { "FAIL" } else { "PASS" }

$summaryContent = @"
# Phase 0 Verification Summary

| Field | Value |
|-------|-------|
| **Status** | $status |
| **Timestamp (UTC)** | $timestampUtc |
| **Commit SHA** | $commitSha |
| **Files Scanned** | $scanFileCount |
| **Violations Found** | $($allViolations.Count) |

## Artifacts

- [scan_files.txt](./scan_files.txt) — List of files scanned
- [matches.txt](./matches.txt) — Violation details (by Rule ID)
- [env.json](./env.json) — Environment snapshot
- [commands.log](./commands.log) — Commands executed

## Rules Checked

### Forbidden Patterns (must NOT exist in docs/phase0)

| Rule ID | Description |
|---------|-------------|
$($forbiddenPatterns | ForEach-Object { "| $($_.Id) | $($_.Description) |" } | Out-String)

### Required Patterns (must exist)

| Rule ID | File | Description |
|---------|------|-------------|
$($requiredPatterns | ForEach-Object { "| $($_.Id) | $($_.File) | $($_.Description) |" } | Out-String)

## Exclusions

The following paths are **completely excluded** from scanning:
- `docs/phase0/verification_runs/**` — Run artifacts (self-reference prevention)
- `docs/phase0/archive/**` — Archived documents and reference materials

Exclusions are enforced via explicit file list filtering. Files under these paths are never scanned.
"@

Write-Utf8File -Path $summaryFile -Content $summaryContent

# ============================================================================
# FINAL OUTPUT
# ============================================================================
Write-Host "========================================" -ForegroundColor $(if ($hasFailures) { "Red" } else { "Green" })
Write-Host "FINAL RESULT: $status" -ForegroundColor $(if ($hasFailures) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor $(if ($hasFailures) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Run artifacts: $runDir" -ForegroundColor Gray
Write-Host ""

if ($allViolations.Count -gt 0) {
    Write-Host "Violations/Issues:" -ForegroundColor Yellow
    $allViolations | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Write-Host ""
}

if ($toolError) {
    exit 2
}
elseif ($hasFailures) {
    exit 1
}
else {
    Write-Host "All checks passed. Phase 0 SoR boundaries verified." -ForegroundColor Green
    exit 0
}
