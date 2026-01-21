# ITAD Core Reporting Contract

> **Version**: 1.0  
> **Last Updated**: 2026-01-18  
> **Change Control**: PRs require review + version bump + Alembic migration

---

## Executive Summary

This document defines the **canonical reporting contract** for ITAD Core.

> [!IMPORTANT]
> **Compliance/financial truth comes from ITAD Core datasets ONLY.**  
> Odoo data is operational telemetry and MUST NOT be used for financial KPIs.

---

## Truth Table

| Metric | Truth Source (SoR) | Allowed Secondary | NOT ALLOWED |
|--------|-------------------|-------------------|-------------|
| received_weight_total_by_stream | ITAD Core `bi.receiving_records_v1` | none | Odoo audit/outbox |
| received_weight_total_by_material | ITAD Core `bi.receiving_records_v1` | none | Odoo fsm_order |
| receiving_cycle_time | ITAD Core (manifest + receiving) | none | Odoo timestamps |
| exception_rate_ops | Odoo telemetry | ITAD Core (if exists) | **NOT financial truth** |
| exception_rate_compliance | ITAD Core (void/reject records) | none | Odoo |
| pricing_coverage | ITAD Core `bi.material_types_v1` | Odoo cache (display) | spreadsheets |

### NOT Truth (Explicitly Excluded)

| Source | Why NOT Truth |
|--------|---------------|
| Odoo `fsm.order.itad_receipt_weight_lbs` | Ops display only, not compliance anchor |
| Odoo `itad.core.outbox` | Telemetry for sync health, not financial |
| Odoo `itad.receipt.audit.log` | Ops audit trail, not compliance record |
| Legacy spreadsheets | Retired, no schema control |

---

## Metrics Catalog

### 1. received_weight_total_by_stream

| Property | Value |
|----------|-------|
| **Definition** | Sum of net received weight grouped by material stream |
| **Formula** | `SUM(net_weight) GROUP BY material_stream` |
| **Grain** | Per stream (e.g., batteries, electronics) |
| **SoR** | ITAD Core |
| **Dataset** | `bi.receiving_records_v1` |
| **Filters** | `is_void = false` |
| **Caveats** | Excludes voided records |

### 2. received_weight_total_by_material_type

| Property | Value |
|----------|-------|
| **Definition** | Sum of net weight grouped by material type code |
| **Formula** | `SUM(net_weight) GROUP BY material_type_code` |
| **Grain** | Per material type |
| **SoR** | ITAD Core |
| **Dataset** | `bi.receiving_records_v1` |
| **Joins** | `bi.material_types_v1` on `material_received_as` |

### 3. receiving_cycle_time

| Property | Value |
|----------|-------|
| **Definition** | Elapsed time from pickup manifest creation to receiving record creation |
| **Formula** | `receiving.occurred_at - manifest.created_at` |
| **Grain** | Per receiving record |
| **SoR** | ITAD Core |
| **Timestamps** | `pickup_manifests.created_at` → `receiving_weight_record_v3.occurred_at` |
| **Unit** | Hours |

### 4. exception_rate_ops (Telemetry Only)

| Property | Value |
|----------|-------|
| **Definition** | Rate of outbox/audit failures in Odoo |
| **Formula** | `COUNT(failed) / COUNT(total)` |
| **SoR** | **Odoo** (telemetry only) |
| **Dataset** | Odoo `itad.core.outbox` + `itad.receipt.audit.log` |
| **Warning** | ⚠️ NOT financial truth |

### 5. exception_rate_compliance

| Property | Value |
|----------|-------|
| **Definition** | Rate of voided receiving records |
| **Formula** | `COUNT(is_void=true) / COUNT(total)` |
| **SoR** | ITAD Core |
| **Dataset** | `bi.receiving_records_v1` |

### 6. pricing_coverage

| Property | Value |
|----------|-------|
| **Definition** | % of material types with pricing configured |
| **Formula** | `COUNT(pricing_state='priced') / COUNT(is_active=true)` |
| **SoR** | ITAD Core |
| **Dataset** | `bi.material_types_v1` |

---

## Canonical Datasets

### bi.material_types_v1

**Source**: `material_types` table  
**Type**: View (read-only)

| Column | Type | Description |
|--------|------|-------------|
| material_type_id | uuid | Primary key |
| code | text | Unique material code |
| name | text | Display name |
| stream | text | Material stream (batteries, electronics, etc.) |
| hazard_class | text | DOT hazard class (nullable) |
| default_action | text | Default processing action |
| requires_photo | boolean | Photo required flag |
| requires_weight | boolean | Weight required flag |
| is_active | boolean | Active flag |
| pricing_state | text | priced/unpriced/contract/deprecated |
| default_price | numeric(12,4) | Default price (nullable) |
| basis_of_charge | text | per_lb/per_kg/per_unit/flat_fee |
| gl_account_code | text | GL account code |
| updated_at | timestamptz | Last update timestamp |

---

### bi.receiving_records_v1

**Source**: `receiving_weight_record_v3` table  
**Type**: View (read-only)

| Column | Type | Description |
|--------|------|-------------|
| receiving_record_id | text | Primary key |
| occurred_at | timestamptz | Receiving timestamp |
| bol_id | text | Bill of Lading ID |
| material_type_code | text | Material type code (denormalized) |
| material_stream | text | Material stream (denormalized) |
| quantity | integer | Container quantity |
| gross_weight | numeric | Gross weight |
| tare_weight | numeric | Tare weight |
| net_weight | numeric | Net weight |
| weight_unit | text | Weight unit (LBS, KG) |
| receiver_employee_id | text | Receiver employee ID |
| is_void | boolean | Voided flag |
| created_at | timestamptz | Record creation time |

---

### bi.receiving_kpis_daily_v1

**Source**: Aggregate view on `receiving_weight_record_v3`  
**Type**: View (read-only)  
**Grain**: Daily

| Column | Type | Description |
|--------|------|-------------|
| report_date | date | UTC date |
| stream | text | Material stream |
| material_type_code | text | Material code (nullable for stream-only) |
| total_net_weight | numeric | Sum of net_weight |
| total_receipts_count | integer | Count of records |

---

### bi.dataset_freshness

**Source**: Table (not view)  
**Purpose**: Monitoring dataset freshness

| Column | Type | Description |
|--------|------|-------------|
| id | serial | Primary key |
| dataset_name | text | e.g., "material_types_v1" |
| dataset_version | text | e.g., "v1" |
| computed_at | timestamptz | When freshness was checked |
| max_source_updated_at | timestamptz | Max updated_at from source |
| row_count | integer | Row count at check time |
| status | text | ok/warn/stale |

---

## Versioning Policy

1. **Never modify existing `*_v1` views** in breaking ways
2. For breaking changes, create `*_v2` and document in change log
3. Deprecate old versions after migration period (6 months minimum)

### Version History

| Dataset | Version | Status | Changes |
|---------|---------|--------|---------|
| material_types | v1 | Active | Initial release |
| receiving_records | v1 | Active | Initial release |
| receiving_kpis_daily | v1 | Active | Initial release |

---

## Freshness SLA

| Dataset | Max Stale | Alert Threshold |
|---------|-----------|-----------------|
| material_types_v1 | 1 hour | > 2 hours |
| receiving_records_v1 | Real-time | > 1 hour |
| receiving_kpis_daily_v1 | 24 hours | > 48 hours |

**Freshness Check Query**:
```sql
SELECT dataset_name, computed_at, status
FROM bi.dataset_freshness
WHERE computed_at > NOW() - INTERVAL '24 hours'
ORDER BY computed_at DESC;
```

---

## Access Control

### Recommended BI Reader Role

```sql
CREATE ROLE bi_reader WITH LOGIN PASSWORD 'xxx';
GRANT USAGE ON SCHEMA bi TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA bi TO bi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA bi GRANT SELECT ON TABLES TO bi_reader;
```

### Access Restrictions

- BI schema is **read-only** for all non-admin roles
- Application service role has no write access to `bi.*`
- Only migration/admin can modify views

---

## Change Control

1. All changes require PR with review
2. Breaking changes require version bump (v1 → v2)
3. New versions require Alembic migration
4. Documentation must be updated with change log

---

## Break-Glass Procedure

If schema changes are needed urgently:

1. Document reason in PR
2. Get ops lead approval
3. Create audit record in `bi.dataset_freshness` with notes
4. Schedule retroactive review within 5 days
