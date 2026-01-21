# Phase 2.4b: Migration Runbook

## Overview

This runbook documents the procedure for migrating legacy material taxonomy from the Categories ROMS.xlsx spreadsheet to ITAD Core database.

## Prerequisites

- [ ] Database backup completed
- [ ] ITAD Core Python environment activated
- [ ] openpyxl installed: `pip install openpyxl`
- [ ] Read access to Categories ROMS.xlsx
- [ ] Write access to ITAD Core database (for apply mode)

## Environment Setup

```bash
cd c:\odoo_dev\itad-core

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install openpyxl
```

## Dry-Run Procedure

**Always run dry-run first** to validate data without making changes.

### Step 1: Execute Dry-Run

```bash
python scripts/migrate_categories_roms.py \
    --input "path/to/Categories ROMS.xlsx" \
    --dry-run \
    --verbose
```

### Step 2: Review Exception Report

Check `docs/evidence/phase2.4/migration_runs/<timestamp>/`:

| File | Contents |
|------|----------|
| `exceptions.json` | Machine-readable validation errors |
| `exceptions.csv` | Human-readable for Excel review |
| `summary.json` | Counts: total, valid, exceptions |

### Step 3: Remediation Workflow

1. Open `exceptions.csv` in Excel
2. For each exception:
   - Review `reason` column
   - Apply `suggested_fix` or custom correction in source
3. Re-run dry-run until exceptions = 0

## Apply Procedure

**Only proceed after dry-run shows 0 exceptions.**

### Step 1: Final Backup

```powershell
# PostgreSQL backup
pg_dump -U postgres itad_core > backup_pre_migration.sql
```

### Step 2: Execute Apply

```bash
python scripts/migrate_categories_roms.py \
    --input "path/to/Categories ROMS.xlsx" \
    --apply \
    --output-dir docs/evidence/phase2.4/migration_runs/apply_$(date +%Y%m%d_%H%M%S)/ \
    --verbose
```

### Step 3: Verify

```sql
-- Check record counts
SELECT COUNT(*), is_active FROM material_types GROUP BY is_active;

-- Verify billing fields
SELECT code, name, default_price, basis_of_charge, gl_account_code 
FROM material_types 
WHERE default_price IS NOT NULL
LIMIT 10;
```

## Rollback Plan

If migration needs to be reverted:

```powershell
# Restore from backup
psql -U postgres itad_core < backup_pre_migration.sql
```

## Evidence Artifacts

All migration runs produce evidence in:
```
docs/evidence/phase2.4/migration_runs/<timestamp>/
├── exceptions.json    # Validation errors
├── exceptions.csv     # Same as CSV for Excel
├── summary.json       # Run statistics
└── run_log.json       # Applied changes (apply mode only)
```

## Validation Rules

| Field | Rule |
|-------|------|
| code | Required, unique |
| name | Required |
| stream | Required, enum: batteries, electronics, etc. |
| hazard_class | Optional |
| default_action | Optional, enum: recycle, dispose, etc. |
| requires_photo | Boolean: true/false, yes/no, 1/0 |
| requires_weight | Boolean: true/false, yes/no, 1/0 |
| default_price | Numeric >= 0 |
| basis_of_charge | Enum: per_lb, per_kg, per_unit, flat_fee |
| gl_account_code | Optional, max 64 chars |

**Mutual Requirement**: `default_price` and `basis_of_charge` must both be set or both be null.

## Troubleshooting

### "Duplicate code" exception
The same code appears on multiple rows. Consolidate or add suffix.

### "Invalid boolean value" exception
Value is not in {true, false, yes, no, 1, 0}. Convert to standard format.

### "Required when default_price is set" exception
Billing fields have mutual requirement. Set both or clear both.

## Post-Migration

1. Run Odoo taxonomy sync to propagate changes
2. Verify cache updated: ITAD Core > Material Types
3. Test receiving wizard with updated materials
4. Archive source spreadsheet with "MIGRATED" label
