# Phase 2.3: Material Taxonomy Sync - Summary

## Overview

Phase 2.3 implements a bidirectional taxonomy sync between **ITAD Core** (System of Record) and **Odoo** (read-only cache consumer). The receiving wizard now uses synced taxonomy with validation flags, degraded mode handling, and concurrency-safe sync.

## System of Record Boundaries

| System | Role | Capabilities |
|--------|------|--------------|
| **ITAD Core** | Authoritative SoR | Create, update, deactivate material types. Owns canonical taxonomy. |
| **Odoo** | Read-only cache | Consume taxonomy via hourly sync. Cannot create/edit/delete taxonomy. Use in wizards. |

## API Contract Summary

### GET /api/v1/material-types

**Public Path**: `/api/v1/material-types`

**Query Parameters**:
- `include_inactive` (bool, default=true): Include inactive records (is_active=false)
- `updated_since` (ISO8601 datetime, optional): Return only records where `updated_at >= updated_since`
- `stream` (string, optional): Filter by stream

**Response Wrapper** (MANDATORY):
```json
{
  "items": [
    {
      "id": "UUID",
      "code": "BAT-LI-001",
      "name": "Lithium Batteries",
      "stream": "batteries",
      "hazard_class": "Class 9",
      "default_action": "recycle",
      "requires_photo": true,
      "requires_weight": true,
      "is_active": true,
      "updated_at": "2026-01-17T20:00:00Z"
    }
  ],
  "meta": {
    "generated_at": "2026-01-17T20:00:00Z",
    "count": 1,
    "include_inactive": true,
    "updated_since": null
  }
}
```

**Canonical Fields**:
- `id`: UUID string (stable, primary key)
- `code`: string, unique
- `name`: string
- `stream`: string
- `hazard_class`: string|null
- `default_action`: string|null
- `requires_photo`: bool
- `requires_weight`: bool
- `is_active`: bool
- `updated_at`: ISO8601 with tz, UTC "Z" preferred

## Odoo Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `itad_core.taxonomy.sync.include_inactive` | true | Sync inactive records |
| `itad_core.taxonomy.sync.incremental_enabled` | true | Use `updated_since` cursor |
| `itad_core.taxonomy.sync.max_stale_hours` | 24 | Max hours since last successful sync |
| `itad_core.taxonomy.sync.timeout_seconds` | 15 | HTTP request timeout |
| `itad_core.taxonomy.sync.block_if_stale` | true | Block receiving if sync is stale |

## How to Run Sync Manually

### Via UI (Recommended)
1. Navigate to **ITAD Core > Configuration > Taxonomy Sync State**
2. Click **Sync Now** button
3. View sync results in notification + stats on form

### Programmatically (Python)
```python
sync_service = env["itad.material.sync"]
result = sync_service._sync_from_itad_core(manual=True)

if result["success"]:
    print(f"Created: {result['stats']['created']}")
    print(f"Updated: {result['stats']['updated']}")
    print(f"Deactivated: {result['stats']['deactivated']}")
else:
    print(f"Error: {result['error']}")
```

## Cron Details

**Cron Job**: `itad_core.ir_cron_material_type_sync`
- **Interval**: 1 hour
- **Model**: `itad.material.sync`
- **Method**: `_sync_from_itad_core(manual=False)`
- **Idempotent**: Yes (uses PostgreSQL advisory lock)

**To modify interval**:
```xml
<record id="itad_core.ir_cron_material_type_sync" model="ir.cron">
    <field name="interval_number">2</field>  <!-- Every 2 hours -->
    <field name="interval_type">hours</field>
</record>
```

## Failure Modes & Troubleshooting

### 1. Sync Lock Acquisition Failure

**Symptom**: `sync already running (could not acquire advisory lock)`

**Cause**: Another sync process is currently running.

**Resolution**: Wait for current sync to finish (usually <30 seconds). If persists, check for stale locks:
```sql
-- Check advisory locks
SELECT * FROM pg_locks WHERE locktype = 'advisory' AND objid = 987654321;

-- Force release (use cautiously)
SELECT pg_advisory_unlock_all();
```

### 2. Empty Cache (Taxonomy Not Synced)

**Symptom**: UserError when trying to receive: `Material taxonomy not synced`

**Cause**: Cache has 0 active records (initial state or all deactivated).

**Resolution**:
1. Click **Sync Now** button
2. Verify ITAD Core `/api/v1/material-types` returns data
3. Check `itad.taxonomy.sync.state` for errors

### 3. Stale Sync Blocking

**Symptom**: UserError: `Material taxonomy is stale (last synced: ...)`

**Cause**: Last successful sync is older than `max_stale_hours` (default 24h) and `block_if_stale=true`.

**Resolution**:
- **Quick Fix**: Click **Sync Now**
- **Disable Blocking** (not recommended):
  ```python
  env['ir.config_parameter'].sudo().set_param('itad_core.taxonomy.sync.block_if_stale', 'false')
  ```

### 4. HTTP Request Timeout

**Symptom**: `HTTP request failed: timeout`

**Cause**: ITAD Core endpoint took > `timeout_seconds` (default 15s).

**Resolution**:
- Increase timeout: `itad_core.taxonomy.sync.timeout_seconds` → `30`
- Check ITAD Core performance/network latency
- Verify ITAD Core is not returning excessive data (use `include_inactive=false` if needed)

### 5. Invalid API Response Format

**Symptom**: `Invalid response format: missing 'items' or 'meta'`

**Cause**: ITAD Core endpoint not returning wrapper format.

**Resolution**:
- Verify ITAD Core version \u003e= 1.0.0 (wrapper format introduced in Phase 2.3)
- Check endpoint returns `{"items": [...], "meta": {...}}`

### 6. Incremental Cursor Issues

**Symptom**: Sync repeatedly fetches same records or misses updates

**Cause**: `last_cursor_updated_since` corrupted or incremental disabled.

**Resolution**:
- Reset cursor:
  ```python
  sync_state = env['itad.taxonomy.sync.state'].get_singleton()
  sync_state.write({'last_cursor_updated_since': False})
  ```
- Verify `itad_core.taxonomy.sync.incremental_enabled` = `true`

## Receiving Wizard Validation Flags

### requires_weight

If material type has `requires_weight=True`, wizard will block submission with ValidationError if `actual_weight_lbs` is 0 or missing.

### requires_photo

If material type has `requires_photo=True`, wizard will block submission with ValidationError if no attachments (`ir.attachment`) exist for the FSM order.

**To attach photos**:
1. Open FSM Order
2. Click **Attachments** icon
3. Upload photo(s)
4. Return to receiving wizard

### hazard_class

If material type has `hazard_class` (e.g., "Class 9"), a warning is logged to `_logger` but submission is NOT blocked. Audit trail records the hazard class for compliance.

## Testing

### ITAD Core Tests

Run from `c:\odoo_dev\itad-core`:
```powershell
python -m pytest tests/test_material_types.py -v
```

Expected: 8 tests pass (wrapper format, include_inactive filter, timezone-aware ISO8601)

### Odoo Tests

Run from `c:\odoo_dev`:
```powershell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http
```

Expected:
- `test_taxonomy_sync.py`: 3 tests pass (create, idempotent, deactivate)
- `test_receiving_wizard_taxonomy.py`: 5 tests pass (domain, requires_weight, requires_photo, degraded modes)

## Maintenance Notes

- **Read-Only Enforcement**: Users cannot manually create/edit/delete cache records. Sync engine uses context `{'itad_sync': True}` to bypass.
- **Deactivation Policy**: Inactive records are set `active=False`, never deleted. Preserves audit trail.
- **Concurrency**: PostgreSQL advisory lock (key 987654321) ensures only one sync runs at a time.
- **Incremental Sync**: Cursor tracks `max(updated_at)` from last response. Reduces bandwidth on subsequent runs.
