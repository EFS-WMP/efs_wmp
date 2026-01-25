# Cleanup old verification runs
$archiveDir = "c:\odoo_dev\docs\phase0\archive\old_verification_runs"
New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null

# Move old runs
Move-Item -Path "c:\odoo_dev\docs\phase0\verification_runs\2026-01-19_213657" -Destination $archiveDir -Force
Move-Item -Path "c:\odoo_dev\docs\phase0\verification_runs\2026-01-19_214305" -Destination $archiveDir -Force
Move-Item -Path "c:\odoo_dev\docs\phase0\verification_runs\2026-01-19_225646" -Destination $archiveDir -Force
Move-Item -Path "c:\odoo_dev\docs\phase0\verification_runs\2026-01-02_2112.txt" -Destination $archiveDir -Force

Write-Host "Cleanup complete. Old verification runs moved to archive." -ForegroundColor Green
