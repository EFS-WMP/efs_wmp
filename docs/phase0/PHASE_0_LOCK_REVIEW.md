# Phase 0 Lock Review

## A) Architecture & Ownership

### A1 — System Boundaries & Ownership (Odoo vs ITAD Core vs Routific) — unambiguous.
Odoo is the system of record for scheduling, work orders, day routes, and dispatch execution. ITAD Core is the system of record for compliance, processing, custody, evidence, reconciliation, lots, shipments, disposition, certificates, and settlement. Routific is optimizer-only and never owns operational truth.

### A2 — Routific is Optimizer-Only (Not System-of-Record)

#### Policy (Non-Negotiable)
- Routific is used only for optimization suggestions (sequence, ETA estimates, distance/time).
- Routific is NOT a system-of-record and must never own operational truth or lifecycle state.
- No write-back: Routific never receives operational status updates; it is not used to store or reconcile execution state.

#### Source of Truth / Ownership Matrix
- **Odoo (System-of-Record for Scheduling/Dispatch):**
  - Pickup Plan
  - Pickup Occurrence
  - Day Route
  - Stops (planned/accepted/actual)
  - Status transitions
  - Actual timestamps
  - Exceptions
- **ITAD Core (System-of-Record for Compliance/Processing):**
  - Manifests/BOL links
  - Weights/containers
  - Audit logs
  - Customer-facing documents
- **Routific (Derived / Transient / Advisory Only):**
  - Optimized stop sequence proposal
  - ETA estimates
  - Distance/time estimates
  - Optional clustering/partitioning
  - Job metadata (routific_job_id, input_hash, timestamps, errors)
- Rule-of-thumb: anything affecting compliance, billing, reporting, or audit must be authored/stored in ITAD Core.

#### Data Flow (Request → Proposal → Acceptance → Execution)
- Odoo builds Optimization Request → Routific returns Optimization Result.
- Odoo stores results as a “Route Proposal” linked to request_id, routific_job_id, input_hash, proposal_version, timestamp.
- Dispatcher accepts/edits in Odoo; execution events recorded in Odoo; compliance artifacts occur in ITAD Core.
- Re-optimization creates a new proposal version; accepted operational state remains authoritative.

#### Storage & Retention Policy
- Persist routific_job_id + input_hash in Odoo always.
- Optionally store raw Routific response JSON for debugging only with TTL (30–90 days).
- ITAD Core may store metadata pointers (routific_job_id/input_hash) for traceability (optional) but is not the SoR for route plans.
- Routific data is never authoritative for compliance/billing/reporting.

#### Single-writer & Idempotency
- Only Odoo/ITAD Core can mutate operational state per domain.
- Optimization calls are idempotent by input_hash; repeated calls must not create conflicting operational records.

#### Failure Modes (Operations must continue)
- Routific down: manual planning/editing in Odoo; do not block operations.
- Optimization error: log “Optimization Attempt”; do not block Day Route creation/execution.
- Partial/low-quality results: store as proposal with flags; dispatcher can override.


### A3 — Glossary exists and is complete (BOL, Receiving Anchor, Workstream, Lot, LPN, Disposition, Settlement, Pickup Manifest).

### A4 — Canonical Object Map exists: Service Plan (Odoo) → Scheduling Rules (Odoo) → Work Order (Odoo) → Pickup Occurrence (Odoo) → Day Route (Odoo) → Stop (Odoo) → Pickup Manifest (ITAD Core) → BOL (ITAD Core) → Receiving Weight Record v3 (ITAD Core) → Processing Sessions (ITAD Core) → Lots + LPN (ITAD Core) → Shipment (ITAD Core) → Disposition (ITAD Core) → Certificates (ITAD Core) → Settlement (ITAD Core).

## B) Identifiers & Versioning

### B1 — BOL# global uniqueness enforced in DB.
- [x] UNIQUE constraint on bol.bol_number implemented and tested.

### B2 — ID/key format policy applied in schema/code.
- [x] UUID v4 for primary keys; BOL number auto-generation (BOL-{SITE}-{YYYY}-{SEQ6}) implemented and tested.

### B3 — External IDs strategy implemented via external_id_map.
- [x] Generic external_id_map schema with UNIQUE(system, entity_type, external_id) and indexes implemented.

### B4 — Customer requirement profiles versioning + snapshot represented.
- [x] BOL schema includes requirement_profile_version, effective_from, snapshot_json fields and API persistence.

## C) Workflow (Gates, Stages, Closure)

### C1 — GATE_TYPE list defined and enforced.
- [x] Minimum set (REQUIREMENTS_CONFIRMED, etc.) in enum; API validates.

### C2 — Append-only rule for bol_stage_gates enforced.
- [x] DB trigger prevents updates/deletes; void pattern implemented.

### C3 — Gate transition matrix implemented.
- [x] BOL and workstream transitions enforced in API.

### C4 — Two-level closure rules enforced.
- [x] Workstream close required before BOL close; API checks.

### C5 — requires_* mechanism defined and persisted.
- [x] Fields in BOL; locked by REQUIREMENTS_CONFIRMED; API sets.

## D) Receiving Anchor (Immutable)

### D1 — Receiving Weight Record v3 contains required fields.
- [x] Required fields list enforced in schema/API.

### D2 — Receiving record immutability enforced.
- [x] Only void/reissue/compensating events; no updates/deletes.

### D3 — Tare policy implemented.
- [x] tare_source enum; no average tare; snapshot validation.

### D4 — Blind Receiving mode implemented.
- [x] Declared weights redacted by default; admin access controlled.
## E) Processing Domains & Taxonomy

### E1 - Battery and E-waste domains defined as session+lines with configurable catalogs.
- [x] Session and line schemas implemented for battery and e-waste with taxonomy linkage.

### E2 - HARD RULE: processing line items require taxonomy_item_id; no free text categories.
- [x] API schemas require taxonomy_item_id; no free-text category fields exist.

### E3 - Taxonomy 3-level defined with governance policy (end-date + new row).
- [x] taxonomy_type/taxonomy_item with effective dates and change log implemented; no delete endpoints.

### E4 - SB20/non-SB20 attributes defined at taxonomy level.
- [x] sb20_flag stored on taxonomy_item and filterable in API.
## F) Reconciliation & Disputes

### F1 - Reconciliation model defined with thresholds and approvals.
- [x] reconciliation_run append-only with variance pct/lbs, thresholds, nonnegative checks, and run_no per BOL.

### F2 - BOL closure blocked on variance over threshold without approval.
- [x] Effective status derived from reconciliation_run + reconciliation_approval_event; over-threshold without APPROVE is a blocker.

### F3 - Discrete discrepancy workflow blocks closure.
- [x] discrepancy_case with open/in_dispute statuses blocks closure until resolved/voided; artifact_refs_json placeholder accepted.
## G) Evidence & Chain of Custody

### G1 - Evidence artifacts layer defined.
- [x] evidence_artifact table with sha256 format check, unique content pointer, visibility, retention, and metadata.

### G2 - artifact_links structure exists.
- [x] artifact_link table linking artifacts to entities with roles and optional visibility override; unique per artifact/entity/role.

### G3 - Chain of Custody append-only defined.
- [x] custody_event table append-only with supersedes_event_id for compensating events; timeline derived by occurred_at.

## H) Inventory, Outbound, Downstream

### H1 - Inventory model exists: LPN/container instances + locations + lots (WIP/READY/SHIPPED/QUARANTINE).
- [x] Tables warehouse_location, lpn_container, inventory_lot, lot_lpn_membership created; statuses enforced in repos; custody_event records moves; membership uses removed_at for history.

### H2 - Outbound shipments domain defined.
- [x] outbound_shipment + shipment_lpn tables; QUARANTINE LPN blocked from loading; dispatch writes custody_event SHIP and sets LPN status SHIPPED; artifacts linked via artifact_link.

### H3 - Downstream qualification + disposition chain defined.
- [x] downstream_vendor + vendor_certification versioned with allowlist flag; disposition_record requires vendor qualification and final_proof_artifact_id; confirm_disposition enforces allowlist+cert+proof; evidence lives in ITAD Core.

## I) Variant A Integrations - Pickup Manifest Bridge

### I1 - Pickup Manifest bridge + BOL binding (items 30, 30.5).
- [x] pickup_manifest schema/state machine exists; bol.pickup_manifest_id FK + unique index; source_type=PICKUP requires binding; state events append-only.

### I2 - Canonical IDs & idempotency (items 30.1, 30.3).
- [x] manifest_no unique; manifest_fingerprint UNIQUE(source_system, manifest_fingerprint); Idempotency-Key required; duplicate attempts return existing manifest.

### I3 - Evidence / POD handling (item 30.4).
- [x] pod_evidence_json stored immutably; policy to link artifacts via artifact_link (Phase 0.G) without in-place edits; visibility rules align to artifact layer.

### I4 - Geocode confidence gating + cache (item 30.6).
- [x] geocode_cache effective-dated with UNIQUE(address_hash, effective_from), confidence gate thresholds (>=0.85 AUTO_ACCEPT, 0.60-0.85 NEEDS_REVIEW, <0.60 MANUAL_REQUIRED); attach_geocode_snapshot_to_manifest uses cache and sets gate.

### I5 - Failure modes, observability, and attempt logging (item 30.7).
- [x] pickup_manifest_integration_attempt logs every inbound attempt with outcome/correlation_id/idempotency_key; transition_manifest_status enforces matrix; VOIDED requires reason; 1 manifest -> 1 BOL binding rule enforced in repo.

## J) Commercials & Tier Pricing Addendum (Policy Lock)

### J1 - Customer Pricing Profile fields + effective dating + approval locked (31.1).
- [x] pricing_external_ref stores immutable Odoo refs/hashes with effective dating and approvals metadata; ITAD Core not authoring pricing.

### J2 - Service catalog / charge types placeholders (31.2).
- [x] pricing_external_ref supports SERVICE_CATALOG; settlement_pricing_snapshot.pricing_payload_json captures catalog rows used.

### J3 - Rule precedence locked (31.3).
- [x] precedence captured inside pricing_payload_json snapshot; ITAD Core does not evaluate rules in Phase 0.

### J4 - Rate card versioning + settlement pricing snapshot locked (31.4).
- [x] settlement_pricing_snapshot is append-only with snapshot_no and hash; references rate card/tier/profile external refs.

### J5 - Basis-of-charge mapping (31.5).
- [x] basis_of_charge_json records computed bases; included in snapshot hash for integrity.

### J6 - Manual adjustments controls (31.6).
- [x] settlement_adjustment_event append-only with reason_text + approver required; signed amount; linked to settlement (optional snapshot).

### J7 - Odoo ↔ ITAD Core pricing exchange policy (31.7).
- [x] External ids + hashes stored (pricing_external_ref, snapshot_hash_sha256); authoring remains in Odoo; no deletes; audit via integration traces.

## Phase 1 Pre-Start Gate
- [ ] Routific caller locked (Odoo vs ITAD Core). Decision recorded + rationale.

## Sign-off Bundle
- `docs/phase0/PHASE_0_SIGNOFF_SUMMARY.md`
- `docs/phase0/PHASE_0_EVIDENCE_INDEX.md`
- `docs/phase0/PHASE_0_VERIFICATION_LOG.md`
- `docs/phase0/PHASE_0_RISK_REGISTER.md`
- `docs/phase0/PHASE_1_READINESS_GATE.md`
