# Test ripgrep with --files-from
$testFile = "c:\odoo_dev\test_files.txt"
$testContent = @"
C:/odoo_dev/docs/phase0/SOR_LOCK.md
"@

[System.IO.File]::WriteAllText($testFile, $testContent, [System.Text.Encoding]::UTF8)

Write-Host "Testing ripgrep with --files-from..."
Write-Host "File list content:"
Get-Content $testFile

Write-Host "`nRunning: rg -n -i 'system' --files-from '$testFile'"
$result = & rg -n -i "system" --files-from $testFile 2>&1
$exitCode = $LASTEXITCODE

Write-Host "`nExit code: $exitCode"
Write-Host "Result:"
$result | ForEach-Object { Write-Host $_ }

# Cleanup
Remove-Item $testFile -ErrorAction SilentlyContinue
