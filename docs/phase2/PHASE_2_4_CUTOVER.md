# Phase 2.4d: Cutover Controls & Spreadsheet Retirement

## Statement of Authority

> **Taxonomy edits happen ONLY in ITAD Core.**
> 
> The Categories ROMS.xlsx spreadsheet is RETIRED as of this cutover.
> All material type changes must be made through ITAD Core.

## Pre-Cutover Checklist

### Verify Sync Health

- [ ] Last sync successful: Check `ITAD Core > Configuration > Taxonomy Sync State`
- [ ] Last sync within 24 hours (or configured max_stale_hours)
- [ ] No error in `last_error` field

### Verify Cache Population

- [ ] Cache non-empty: `ITAD Core > Material Types` shows records
- [ ] Active materials present: Filter by Active = True
- [ ] Billing fields present: Check `Default Price`, `Basis of Charge` columns

### Verify Billing Fields

Check top 10 high-volume materials have billing metadata:
```sql
SELECT code, name, default_price, basis_of_charge, gl_account_code
FROM material_types
WHERE is_active = TRUE
ORDER BY code
LIMIT 10;
```

### Verify Odoo Cache

```python
# In Odoo shell
env['itad.material.type.cache'].search_count([('active', '=', True)])
# Should match ITAD Core active count
```

## Post-Cutover Procedures

### Archive Spreadsheet

1. Rename spreadsheet to `Categories ROMS - RETIRED 2026-01-18.xlsx`
2. Move to archive folder
3. Remove from shared drives / update permissions to read-only

### Update Documentation

1. Remove spreadsheet references from SOPs
2. Document ITAD Core as source for material types
3. Update training materials

### Monitor

For 2 weeks post-cutover:
- Daily check of sync health
- Monitor audit logs for sync failures
- Verify wizard operates correctly

## Break-Glass Procedure

In case of emergency where taxonomy sync is not working:

### Step 1: Enable Break-Glass

```python
# In Odoo shell (with admin access)
icp = env['ir.config_parameter'].sudo()
icp.set_param('itad_core.taxonomy.sync.break_glass_enabled', 'true')

# Document reason in sync state
sync_state = env['itad.taxonomy.sync.state'].get_singleton()
sync_state.write({
    'break_glass_reason': 'Emergency override - ITAD Core API unreachable - Ticket#12345'
})
```

### Step 2: Audit Event

Break-glass usage is automatically logged to `itad.taxonomy.audit.log` with action `stale_override_used`.

### Step 3: Resolution

After fixing the issue:
```python
icp.set_param('itad_core.taxonomy.sync.break_glass_enabled', 'false')
# Clear reason
sync_state.write({'break_glass_reason': False})
# Trigger immediate sync
env['itad.material.sync'].action_sync_now()
```

## Wizard Guardrails

The receiving wizard enforces these guardrails:

| Condition | Behavior |
|-----------|----------|
| Cache empty | **BLOCKS** submission with error |
| Cache stale + block_if_stale=true + break_glass=false | **BLOCKS** submission |
| Cache stale + break_glass=true | **WARNS** + creates audit event |
| Material requires_photo + no attachments | **BLOCKS** submission |
| Material requires_weight + weight=0 | **BLOCKS** submission |

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `itad_core.taxonomy.sync.block_if_stale` | `true` | Block if taxonomy is stale |
| `itad_core.taxonomy.sync.max_stale_hours` | `24` | Hours before considered stale |
| `itad_core.taxonomy.sync.break_glass_enabled` | `false` | Override stale blocking |

## Rollback Plan

If cutover causes critical issues:

1. **Immediate**: Enable break-glass to unblock operations
2. **Short-term**: Investigate and fix sync issues
3. **If prolonged**: Manually update cache via integration group user

```python
# Emergency manual cache update (requires integration group)
cache = env['itad.material.type.cache'].sudo()
cache.create({
    'itad_core_uuid': 'emergency-uuid-001',
    'code': 'EMERGENCY-001',
    'name': 'Emergency Material',
    'stream': 'other',
    'active': True,
    ...
})
```

## Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Operations Manager | | | |
| IT Manager | | | |
| Compliance | | | |
