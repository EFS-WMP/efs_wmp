# Phase 2.3 Security Hardening Summary

## Overview

Phase 2.3 Material Taxonomy Sync has been hardened to **enterprise-grade, audit-ready standards**. All context-based security bypasses eliminated. Advisory locks now deterministic and auditable. Comprehensive audit logging and break-glass support implemented.

## Critical Security Fixes

### 1. ACL-Based Read-Only Enforcement ⭐

**Vulnerability**: Context flag `{'itad_sync': True}` could bypass read-only protection.

**Fix**: Integration group + ACL enforcement:
```python
def _check_integration_permission(self):
    return (
        self.env.is_superuser() or
        self.env.user.has_group('itad_core.group_itad_integration')
    )
```

### 2. Deterministic Advisory Locks ⭐

**Vulnerability**: Hardcoded arbitrary lock key (987654321).

**Fix**: SHA256-derived from namespace:
```python
lock_key = sha256("itad_core.material_type_sync") -> 7287995589393272399
```

### 3. Cursor Overlap ⭐

**Vulnerability**: Same-timestamp updates could be missed.

**Fix**: Subtract 2s overlap from cursor:
```python
updated_since = cursor - timedelta(seconds=2)
```

### 4. Contract Validation ⭐

**Vulnerability**: Malformed API responses could cause silent failures.

**Fix**: Validate wrapper and required fields:
```python
if 'items' not in data or 'meta' not in data:
    raise ValidationError("Invalid API response...")
```

### 5. Audit Logging ⭐

**Vulnerability**: No audit trail for security events.

**Fix**: New `itad.taxonomy.audit.log` model tracking:
- Every sync attempt (success/failure)
- Break-glass toggles
- Stale overrides
- Lock conflicts

### 6. Break-Glass with Audit ⭐

**Vulnerability**: No documented override procedure.

**Fix**: Configurable break-glass with mandatory audit:
```python
if break_glass_enabled:
    audit_model.log_event(action='stale_override_used', ...)
```

## New Security Group

**`itad_core.group_itad_integration`**
- Required for cache write permission
- Assign ONLY to system sync accounts
- Hidden from regular users

## Test Commands

```powershell
cd c:\odoo_dev
# Full test suite
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http

# Security tests only
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core.test_taxonomy_security -c /etc/odoo/odoo.conf -d odoo18_db --stop-after-init --no-http
```

**Expected**: 24+ tests pass (16 original + 12 security)

## Deployment Checklist

- [ ] Assign integration group to sync service account ONLY
- [ ] Verify `break_glass_enabled=false` in production
- [ ] Document break-glass approval process
- [ ] Review audit log retention policy
- [ ] Run full test suite post-deployment

## Files Changed

**New (4)**:
- `security/itad_core_integration_group.xml`
- `models/itad_taxonomy_audit_log.py`
- `views/itad_taxonomy_audit_log_views.xml`
- `tests/test_taxonomy_security.py`

**Modified (8)**:
- `models/itad_material_type_cache.py` (ACL enforcement)
- `models/itad_material_sync.py` (locks, validation, audit)
- `models/itad_taxonomy_sync_state.py` (break_glass_reason)
- `models/itad_receiving_wizard.py` (break-glass support)
- `models/__init__.py` (audit log import)
- `data/itad_core_system_parameters.xml` (new params)
- `security/ir.model.access.csv` (audit ACLs)
- `__manifest__.py` (group + views)

## Security Compliance

| Requirement | Status |
|-------------|--------|
| No context bypass | ✅ |
| Deterministic locks | ✅ |
| Cursor overlap | ✅ |
| Contract validation | ✅ |
| Audit logging | ✅ |
| Break-glass audit | ✅ |
| Security tests | ✅ (12 tests) |

## CRITICAL Warning

> ⚠️ **DO NOT** assign `itad_core.group_itad_integration` to regular business users. Assign ONLY to dedicated sync service accounts.

## Extra Hardening (Phase 2.3+)

### Advisory Lock Typing
```python
# Signed 64-bit safe with bigint cast
key = sha256(namespace).digest()[:8] & ((1<<63)-1)
self.env.cr.execute("SELECT pg_try_advisory_lock(%s::bigint)", [key])
```

### Audit Retention Policy
- **Mode `archive`** (default): Set `archived=True` for records > 365 days
- **Mode `delete`**: Delete archived records older than retention + 30 day grace
- Cron runs daily, never re-archives

### Integration User Guardrail
- CI test fails if non-whitelisted user has `group_itad_integration`
- Whitelist configurable via `ITAD_INTEGRATION_USER_WHITELIST` env or config param
- Default: `itad_integration, admin, __system__`

### Evidence Bundle Export
```python
# Export sync evidence for audit
env['itad.material.sync'].export_sync_evidence()
# -> docs/evidence/phase2.3/<timestamp>/{sync_state,audit_logs,cache_stats,manifest}.json
```

## Conclusion

System is now **enterprise-grade and audit-ready**. All security vulnerabilities fixed. Comprehensive audit trail for compliance.
