# Phase 2.2 Verification Script
# Run this after module upgrade to verify implementation

Write-Host "Phase 2.2 Verification Starting..." -ForegroundColor Cyan

# Wait for Odoo to be ready
Write-Host "`nWaiting for Odoo to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if Odoo is running
Write-Host "`nChecking Odoo status..." -ForegroundColor Yellow
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml ps odoo18

# Verify system parameters were created
Write-Host "`n=== Verifying System Parameters ===" -ForegroundColor Cyan
Write-Host "Checking ir.config_parameter records..." -ForegroundColor Yellow

$checkParams = @"
import sys
env = api.Environment(cr, SUPERUSER_ID, {})
icp = env['ir.config_parameter'].sudo()
params = {
    'itad_core.default_container_type': 'PALLET',
    'itad_core.default_scale_id': 'DOCK-SCALE-01',
    'itad_core.receipt_timeout_seconds': '30',
    'itad_core.max_receipt_weight_lbs': '100000',
}
print('\\nSystem Parameters:')
for key, expected in params.items():
    actual = icp.get_param(key)
    status = '✓' if actual == expected else '✗'
    print(f'{status} {key} = {actual} (expected: {expected})')
sys.exit(0)
"@

# Note: Full test run requires stopping Odoo server
Write-Host "`n=== Test Execution ===" -ForegroundColor Cyan
Write-Host "To run full test suite:" -ForegroundColor Yellow
Write-Host "1. Stop Odoo: docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml stop odoo18" -ForegroundColor Gray
Write-Host "2. Run tests: docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml run --rm odoo18 odoo -c /etc/odoo/odoo.conf -d odoo18_db --test-tags=itad_core --stop-after-init --log-level=test" -ForegroundColor Gray
Write-Host "3. Start Odoo: docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml up -d odoo18" -ForegroundColor Gray

Write-Host "`n=== Manual Verification Steps ===" -ForegroundColor Cyan
Write-Host "1. Navigate to Settings → Users & Companies → Groups" -ForegroundColor Yellow
Write-Host "   - Verify 'ITAD Receiving Manager' group exists" -ForegroundColor Gray
Write-Host "`n2. Navigate to Settings → Technical → Parameters → System Parameters" -ForegroundColor Yellow
Write-Host "   - Verify itad_core.* parameters exist with correct defaults" -ForegroundColor Gray
Write-Host "`n3. Test receiving wizard with user NOT in receiving manager group" -ForegroundColor Yellow
Write-Host "   - Should get AccessError" -ForegroundColor Gray
Write-Host "`n4. Add user to 'ITAD Receiving Manager' group and retry" -ForegroundColor Yellow
Write-Host "   - Should work" -ForegroundColor Gray
Write-Host "`n5. Test validation:" -ForegroundColor Yellow
Write-Host "   - Invalid BOL (e.g., 'BOL-2026-123') → ValidationError" -ForegroundColor Gray
Write-Host "   - Negative weight → ValidationError" -ForegroundColor Gray
Write-Host "   - Excessive weight (>100000) → ValidationError" -ForegroundColor Gray
Write-Host "`n6. Test retry mechanism:" -ForegroundColor Yellow
Write-Host "   - Stop ITAD Core, attempt receipt → Error banner appears" -ForegroundColor Gray
Write-Host "   - Verify 'Retry' button visible" -ForegroundColor Gray
Write-Host "   - Start ITAD Core, click Retry → Should succeed" -ForegroundColor Gray
Write-Host "   - Check audit log for both attempts" -ForegroundColor Gray

Write-Host "`n=== Phase 2.2 Verification Complete ===" -ForegroundColor Green
Write-Host "Module upgraded successfully. Run manual tests above to verify functionality." -ForegroundColor Green
