# Phase 2.5 Evidence Artifacts

This directory stores test run logs and verification evidence for Phase 2.5.

## Test Run Logs

After running tests, save output here:

```powershell
cd c:\odoo_dev
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http `
  2>&1 | Tee-Object -FilePath docs/evidence/phase2.5/test_run_YYYYMMDD.log
```

## Expected Evidence Files

| File | Contents |
|------|----------|
| `test_run_YYYYMMDD.log` | Full test output |
| `alert_compute_log.txt` | Sample compute_alerts() output |
| `variance_queue_screenshot.png` | UI verification |

## Verification Checklist

- [ ] All tests pass
- [ ] Dashboard shows 3 alert cards
- [ ] Variance queue functional
- [ ] Crons registered and running
