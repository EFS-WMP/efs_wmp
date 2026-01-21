# Phase 2.4 Summary: Taxonomy Billing Metadata & Legacy Migration

## Overview

Phase 2.4 extends the material taxonomy with billing metadata, adds legacy spreadsheet migration tooling, provides operational reports, and establishes cutover controls for spreadsheet retirement.

> [!IMPORTANT]
> **No Automated Billing**: This phase adds billing metadata fields only. No automated invoice or billing generation is implemented.

## Components Delivered

### 2.4a - Billing Metadata Schema + API

**ITAD Core (FastAPI)**:
- Extended `MaterialType` model with:
  - `default_price` (NUMERIC 12,4)
  - `basis_of_charge` (per_lb, per_kg, per_unit, flat_fee)
  - `gl_account_code` (VARCHAR 64)
- Database constraints: mutual requirement, enum validation, positive price
- Alembic migration #0012
- Updated API response includes billing fields

**Odoo (itad_core addon)**:
- Extended `itad.material.type.cache` with matching fields
- Sync service maps billing fields with hash-based change detection

### 2.4b - Legacy Migration Tool

**Script**: `itad-core/scripts/migrate_categories_roms.py`

```bash
# Dry-run (default)
python scripts/migrate_categories_roms.py --input "Categories ROMS.xlsx" --dry-run

# Apply
python scripts/migrate_categories_roms.py --input "Categories ROMS.xlsx" --apply
```

**Features**:
- Excel parsing via openpyxl
- Field validation (required, enums, numerics, booleans)
- Deterministic exception reports (JSON + CSV)
- Idempotent upsert by code

### 2.4c - Operational Reports

Two reports under **ITAD Core > Reports**:
- **Received Weight by Material** (pivot/list view)
- **Customer Receipt History** (list view)

Security: Receiving Manager role only.

### 2.4d - Cutover Controls

- Cutover documentation: `docs/phase2/PHASE_2_4_CUTOVER.md`
- Pre-cutover checklist
- Break-glass procedure
- Wizard guardrails (blocks on empty cache)

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `itad_core.taxonomy.audit_retention_days` | 365 | Days before archiving audit logs |
| `itad_core.taxonomy.audit_retention_mode` | archive | archive or delete |

## Files Changed

### ITAD Core

| File | Change |
|------|--------|
| `app/models/material_type.py` | Added billing fields + constraints |
| `app/schemas/material_type.py` | Added billing fields to response |
| `alembic/versions/0012_phase2_4a_billing_metadata.py` | Migration |
| `tests/test_material_types.py` | Added 4 billing tests |
| `scripts/migrate_categories_roms.py` | NEW - Migration tool |

### Odoo

| File | Change |
|------|--------|
| `models/itad_material_type_cache.py` | Added billing fields |
| `models/itad_material_sync.py` | Billing field mapping + hash |
| `views/itad_operational_reports_views.xml` | NEW - Reports |
| `__manifest__.py` | Added reports view |

### Documentation

| File | Purpose |
|------|---------|
| `docs/phase2/PHASE_2_4_SUMMARY.md` | This document |
| `docs/phase2/PHASE_2_4_MIGRATION_RUNBOOK.md` | Migration procedure |
| `docs/phase2/PHASE_2_4_CUTOVER.md` | Cutover controls |

## Test Commands

### ITAD Core

```bash
cd c:\odoo_dev\itad-core
pytest tests/test_material_types.py -v
```

### Odoo

```powershell
cd c:\odoo_dev
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http
```

### Migration Dry-Run

```bash
cd c:\odoo_dev\itad-core
python scripts/migrate_categories_roms.py --input "Categories ROMS.xlsx" --dry-run --verbose
```

**Output**: `docs/evidence/phase2.4/migration_runs/<timestamp>/`
- `exceptions.json` - Validation errors
- `exceptions.csv` - Same for Excel
- `summary.json` - Run statistics

## Verification

- [ ] ITAD Core API returns billing fields
- [ ] Odoo cache shows billing fields after sync
- [ ] Migration dry-run produces deterministic reports
- [ ] Operational reports render for receiving managers
- [ ] Wizard blocks on empty taxonomy cache

---

## Evidence Artifacts (Auditor Reference)

### Migration Evidence

**Location**: `docs/evidence/phase2.4/migration_runs/<timestamp>/`

| File | Contents |
|------|----------|
| `summary.json` | Row counts, has_duplicates, apply_blocked |
| `exceptions.json` | Validation errors (machine-readable) |
| `exceptions.csv` | Same (Excel-friendly) |

### Retention Audit Events

**Where to view**: Odoo → ITAD Core → Configuration → Taxonomy Audit Logs

**Filter**: `action = 'retention_delete'`

**Fields logged**:
- Who: `user_id` (cron = OdooBot)
- When: `occurred_at`
- What: `details` (count, retention_days, threshold)

### Admin Permissions

| Config Parameter | Who Can Set | Purpose |
|-----------------|-------------|---------|
| `audit_retention_mode` | Admin | archive (default) or delete |
| `audit_retention_delete_enabled` | Admin | Must be `true` to allow deletion |

**Access**: Odoo → Settings → System Parameters (admin only)

> [!NOTE]
> Delete mode is blocked at runtime until `audit_retention_delete_enabled=true`.
> All deletions are logged **before** execution for compliance.
