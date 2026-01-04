# Canonical Object Map (Phase 0 Locked)

## Canonical Chain
Service Plan (Odoo) -> Scheduling Rules (Odoo) -> Work Order (Odoo) -> Pickup Occurrence (Odoo) -> Day Route (Odoo) -> Stop (Odoo) -> Pickup Manifest (ITAD Core; created when Odoo work order is completed, includes POD evidence + route/stop snapshots) -> BOL (ITAD Core; source_type=PICKUP when coming from pickup) -> Receiving Weight Record v3 (ITAD Core immutable anchor) -> Processing Sessions (Battery/E-waste; taxonomy-linked) -> Lots + LPN (ITAD Core inventory with custody events) -> Outbound Shipment (ITAD Core) -> Downstream Vendor / Disposition + Final Proof (ITAD Core; evidence via artifact_link) -> Certificates (ITAD Core) -> Settlement (ITAD Core)

### Routing (Decision Locked)
- Odoo Day Route -> Routific Proposal(s) (Odoo; stored/versioned in Odoo) -> Acceptance/Dispatch (Odoo) -> Completion -> Pickup Manifest (ITAD Core) -> BOL -> Receiving...

## Object Details

### Service Plan
- **SoR:** Odoo
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** Odoo
- **How it is created:** Customer agreement in Odoo UI

### Scheduling Rules
- **SoR:** Odoo
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** Odoo
- **How it is created:** Configured in Odoo for recurring schedules

### Work Order
- **SoR:** Odoo
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** Odoo
- **How it is created:** Generated from Service Plan or manual creation in Odoo

### Pickup Occurrence
- **SoR:** Odoo
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** Odoo
- **How it is created:** Scheduled from Work Order in Odoo

### Day Route
- **SoR:** Odoo
- **Primary ID:** uuid
- **External IDs:** routific_job_id (optional, for traceability)
- **Who can write:** Odoo
- **How it is created:** Planned in Odoo, optimized via Routific proposals

### Stop
- **SoR:** Odoo
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** Odoo
- **How it is created:** Part of Day Route planning in Odoo

### Pickup Manifest
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** odoo_work_order_id, odoo_pickup_occurrence_id, odoo_day_route_id, odoo_stop_id (stored in ITAD Core external_id_map)
- **Who can write:** ITAD Core
- **How it is created:** Created in ITAD Core when Odoo work order is completed; includes POD evidence + route/stop snapshots; SoR wording lock: Acceptance/dispatch commits to Odoo; ITAD Core receives compliance artifacts later via pickup_manifest -> BOL -> receiving...
- **Governance:** State machine DRAFT -> SUBMITTED -> BOUND_TO_BOL -> RECEIVED -> CLOSED; VOIDED terminal with reason. manifest_fingerprint + Idempotency-Key prevent duplicates; pickup_manifest_integration_attempt logs outcomes; geocode_cache snapshot sets gate (AUTO_ACCEPT/NEEDS_REVIEW/MANUAL_REQUIRED); binding rule 1 manifest -> 1 BOL when source_type=PICKUP.

### BOL
- **SoR:** ITAD Core
- **Primary ID:** uuid (internal); bol_number (human-readable, auto-generated BOL-{SITE}-{YYYY}-{SEQ6}, globally unique)
- **External IDs:** odoo_* ids (stored in ITAD Core external_id_map table)
- **Who can write:** ITAD Core
- **How it is created:** Generated in ITAD Core; source_type=PICKUP when coming from pickup; gates emitted as append-only bol_stage_gates.

### Receiving Weight Record v3
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** Immutable inbound anchor created during receiving in ITAD Core; corrections via receiving_record_voids (void) and reissue_of_id (reissue); tare policy enforced; blind receiving redaction optional.

### Processing Sessions
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** Session + lines for Battery and E-waste; every line references taxonomy_item_id (no free-text categories); sb20_flag lives on taxonomy_item; governance via effective dating.

### Warehouse Location
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** Configured with stable site_code/location_code and location_type (dock/scale/storage/quarantine/outbound). Deactivate instead of delete. Movements reference locations via custody_event.

### Lots + LPN
- **SoR:** ITAD Core
- **Primary ID:** uuid (Lot), uuid (LPN)
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** LPN/container instances created at receiving/processing with status WIP/READY/SHIPPED/QUARANTINE and current_location_id convenience pointer; custody_events record moves. inventory_lot created with taxonomy_item_id (hard rule) and optional bol_id; lot_lpn_membership is append-only with removed_at history.

### Shipment
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** Assembled from Lots/LPN; outbound_shipment stores carrier/appointment/seal/hazmat; shipment_lpn contents; QUARANTINE LPNs blocked; dispatch emits custody_event SHIP per LPN; artifacts (seals/hazmat docs) linked via artifact_link.

### Disposition
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** disposition_record links lot -> downstream_vendor (optionally shipment) with disposition_type/status; confirmation requires allowlisted vendor, active certification, and final_proof_artifact_id; artifacts linked via artifact_link.

### Certificates
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** None
- **Who can write:** ITAD Core
- **How it is created:** Generated for compliance in ITAD Core; tied to disposition/final proof.

### Settlement
- **SoR:** ITAD Core
- **Primary ID:** uuid
- **External IDs:** References Odoo pricing artifacts via pricing_external_ref (customer profile, service catalog, rate card, tier ruleset).
- **Who can write:** ITAD Core (snapshots/adjustments only; Odoo authors pricing).
- **How it is created:** Settlement created per BOL; settlement_pricing_snapshot records immutable pricing payload/bases/lines with snapshot_hash_sha256; pricing_external_ref stores Odoo ids + hashes; settlement_adjustment_event append-only with approver/reason.

## Integration Notes
- external_id_map required in ITAD Core for Odoo references.
- Idempotency-Key required on ITAD Core create APIs.
- Routific proposals are advisory; acceptance changes Odoo route/stop plan only.
- Pickup-to-Receiving bridge: pickup_manifest required when BOL.source_type=PICKUP.
