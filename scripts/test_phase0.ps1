<#
.SYNOPSIS
    Test script for Phase 0 verification
#>

param()

Write-Host "Starting test..."

# Test 1: Set location
Write-Host "Test 1: Set-Location"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Write-Host "  scriptDir: $scriptDir"
$rootDir = Split-Path -Parent $scriptDir
Write-Host "  rootDir: $rootDir"
Set-Location -Path $rootDir

# Test 2: Check rg
Write-Host "Test 2: Check ripgrep"
$rgPath = Get-Command rg -ErrorAction SilentlyContinue
if ($rgPath) {
    Write-Host "  rg found at: $($rgPath.Source)"
}
else {
    Write-Host "  rg NOT FOUND"
    exit 2
}

# Test 3: Create timestamp folder
Write-Host "Test 3: Create run folder"
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$runDir = Join-Path $rootDir "docs\phase0\verification_runs\$timestamp"
Write-Host "  Creating: $runDir"
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

# Test 4: Write test file
Write-Host "Test 4: Write test file"
$testFile = Join-Path $runDir "test.txt"
"Test content" | Out-File $testFile -Encoding UTF8

Write-Host "Test passed! Run dir: $runDir"
exit 0
