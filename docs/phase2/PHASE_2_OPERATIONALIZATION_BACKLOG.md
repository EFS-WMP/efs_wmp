# Phase 2 Operationalization Backlog & Technical Notes

## Non-negotiable SoR Boundaries
- **Odoo SoR:** planning/dispatch and field execution (FSM orders, routes, stops).
- **ITAD Core SoR:** compliance/receiving artifacts (BOL, receiving weight records, custody/evidence, reconciliation).
- **Reporting rule:** Odoo stores **snapshots only** for compliance; it must not become the source of truth.

## Prioritized Backlog (Dashboards / Reports / Extracts)

### P0 — Ops Daily Dispatch Dashboard
- **Purpose:** Daily execution visibility for dispatch leads.
- **Models/Fields:**
  - `fsm.order`: `stage_id`, `date_start`, `date_end`, `scheduled_date`, `location_id`, `partner_id`, `team_id`, `priority`, `name`.
  - `fsm.location`: `name`, `partner_id`, `city`, `state_id`.
- **SoR Owner:** Odoo (operational truth).
- **Security Groups:** `base.group_user`; optional dispatch manager group if defined.
- **Performance Notes:**
  - Add indexes on `fsm.order` date fields if query volume is high.
  - Prefer stored fields for computed customer/location names.
- **Pre-Prod Validation:**
  - Seed FSM orders across stages/teams and validate counts by stage/team.

### P0 — Pickup Manifest Submission Health
- **Purpose:** Monitor outbox queue health and integration status.
- **Models/Fields:**
  - `itad.core.outbox`: `state`, `attempt_count`, `next_retry_at`, `last_http_status`, `dead_letter_reason`, `last_error`, `order_id`.
  - `fsm.order`: `itad_submit_state`, `itad_last_submit_at`.
- **SoR Owner:** Odoo for submission telemetry; ITAD Core remains SoR for compliance.
- **Security Groups:** `group_receiving_manager` (ops) + integration group (read-only view for non-ops).
- **Performance Notes:**
  - Index `itad.core.outbox.state`, `next_retry_at`.
  - Avoid heavy joins in list views; use action filters.
- **Pre-Prod Validation:**
  - Simulate failed and dead-letter states; verify filters/counts.

### P0 — Receiving Confirmation Status
- **Purpose:** Ops view of which pickups have receipt confirmations.
- **Models/Fields:**
  - `fsm.order`: `itad_receipt_state`, `itad_receipt_confirmed_at`, `itad_receipt_weight_lbs`, `itad_receipt_material_code`.
- **SoR Owner:** ITAD Core (compliance). Odoo stores snapshot fields only.
- **Security Groups:** `group_receiving_manager` (read-only fields).
- **Performance Notes:**
  - Use stored fields only; avoid computed aggregations.
- **Pre-Prod Validation:**
  - Confirm snapshots update on receiving flow and remain read-only.

### P1 — Compliance Exception Queue
- **Purpose:** Surface receiving exceptions without mutating compliance truth.
- **Models/Fields:**
  - `fsm.order`: `itad_receipt_state = 'exception'`, `itad_last_error`, `itad_receipt_notes`.
  - `itad.receipt.audit.log`: `created_at`, `outcome`, `details` (read-only).
- **SoR Owner:** ITAD Core (audit log), Odoo snapshot only.
- **Security Groups:** `group_receiving_manager`.
- **Performance Notes:**
  - Ensure audit log indexes on `created_at` and `outcome`.
- **Pre-Prod Validation:**
  - Force a receiving exception; confirm audit log visibility.

### P1 — Daily Compliance Extract (CSV)
- **Purpose:** Export compliance snapshots for stakeholders.
- **Models/Fields:**
  - `fsm.order`: receipt snapshot fields + manifest identifiers.
  - `itad.receipt.audit.log`: latest outcome per order (optional).
- **SoR Owner:** ITAD Core (authoritative); extract is a snapshot from Odoo.
- **Security Groups:** `group_receiving_manager` + export permission.
- **Performance Notes:**
  - Filter by date range; batch exports for large datasets.
- **Pre-Prod Validation:**
  - Spot-check exported rows against ITAD Core records.

### P2 — Taxonomy Sync Health
- **Purpose:** Ops visibility into taxonomy sync status.
- **Models/Fields:**
  - `itad.taxonomy.sync.state`: `last_success_at`, `last_attempt_at`, `last_error`, `sync_state`, `stale_age_hours`.
- **SoR Owner:** Odoo for sync telemetry only; ITAD Core remains SoR for taxonomy truth.
- **Security Groups:** `group_receiving_manager` (read-only), integration group for actions.
- **Performance Notes:**
  - Singleton model; minimal performance risk.
- **Pre-Prod Validation:**
  - Simulate sync failure; verify UI state changes without write access.

## Vertical Slice Spec (Ready for Implementation)
**Slice:** Pickup Manifest Submission Health (P0)
- **Scope:** Outbox list view + filters + KPI tiles.
- **KPIs:** Pending count, Failed (retrying) count, Dead-letter count.
- **Filters:** `state = pending`, `state = failed`, `state = dead_letter`.
- **Performance Target:** list view loads under 2s on pre-prod dataset.
- **Acceptance Criteria:**
  - KPI counts match filtered list totals.
  - No SoR violations (no mutation of FSM operational fields).
  - Screenshots captured for evidence packet (`docs/evidence/phase2.2/screenshots/`).
