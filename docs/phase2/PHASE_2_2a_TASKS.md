# Phase 2.2a - Core Hardening Tasks

## Overview
Production-blocking hardening features for receiving dashboard: API health checks, rate limiting, contract validation, audit archiving.

## Verification Commands

### 1. Upgrade Module
```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 `
  odoo -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init
```

### 2. Run Tests
```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 `
  odoo -c /etc/odoo/odoo.conf -d odoo18_db --test-tags=itad_core --stop-after-init --test-enable
```

### 3. XML Guard Test (No attrs/states)
```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 `
  sh -lc "(! grep -RIn --include='*.xml' -E '\b(attrs|states)\s*=' /mnt/extra-addons-custom/itad_core)"
```

## Implementation Checklist

### Code
- [x] Add `_now()` deterministic time wrapper to wizard
- [x] Add `_check_itad_core_compatibility()` for API health/version checks
- [x] Add `_check_rate_limit()` for max attempts per hour
- [x] Update `_log_receipt_attempt()` to accept outcome parameter
- [x] Update `action_confirm_receipt()` to call new checks
- [x] Add outcome field to audit log model
- [x] Add archived fields to audit log model
- [x] Add `_cron_archive_old_receipt_audit_logs()` method
- [x] Add user_id and bol_id to audit log

### Data Files
- [x] Create `itad_core_system_parameters.xml` with all parameters
- [x] Create `itad_receipt_audit_archiving_cron.xml`
- [x] Update `__manifest__.py` to include new data files

### Tests
- [x] Contract integration tests (7 tests)
- [x] API health/version compatibility tests (4 tests)
- [x] Rate limiting tests (3 tests)
- [x] Audit archiving tests (3 tests)
- [x] Register all tests in `tests/__init__.py`

### Documentation
- [x] Update tasks.md with verification commands
- [ ] Update manifest.md with Phase 2.2a summary
- [ ] Update implementation_plan.md

## System Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `itad_core.default_container_type` | `PALLET` | Default container type |
| `itad_core.default_scale_id` | `DOCK-SCALE-01` | Default scale ID |
| `itad_core.receipt_timeout_seconds` | `30` | API timeout in seconds |
| `itad_core.max_receipt_weight_lbs` | `100000` | Maximum weight in lbs |
| `itad_core.bol_pattern` | `^BOL-\d{4}-\d{6}$` | BOL format regex |
| `itad_core.max_receipt_attempts_per_hour` | `10` | Rate limit |
| `itad_core.audit_retention_days` | `180` | Audit log retention |

## Success Criteria
- ✅ All tests pass
- ✅ No attrs/states in XML
- ✅ API health check blocks incompatible versions
- ✅ Rate limiting enforced
- ✅ Contract schema validated
- ✅ Audit logs archived after retention period
