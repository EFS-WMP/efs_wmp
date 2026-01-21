Phase 2: Digital Taxonomy & Receiving Workflow - Technical Delivery Document
Document Version: 1.0
Project: Modern Waste Recycling Platform (MWRP)
Date: 2024-01-17
Status: IN PROGRESS (2.1 Complete, 2.2/2.3 in development)

1. Overview
1.1 Purpose of Phase 2
Phase 2 establishes the critical digital bridge between field operations (pickup) and facility compliance (receiving). Its primary purpose is to transform the completed pickup_manifest (from Phase 1) into an immutable, auditable receiving_weight_record_v3 within ITAD Core, using a user-driven workflow in Odoo. This phase introduces the authoritative material taxonomy, forming the "golden thread" for classification, compliance, and future billing.

1.2 Key Business Drivers
Operational Efficiency: Replace paper-based receiving tickets and manual data entry with a fast, 3-click digital workflow for the Shipping & Receiving Manager.

Compliance Assurance: Enforce the creation of immutable compliance records (receiving_weight_record_v3) as a direct, traceable result of physical material intake, satisfying R2v3 and NIST 800-88 audit requirements.

Data Foundation: Create a single, authoritative source for material classification (taxonomy) to eliminate errors from disparate spreadsheets (Categories ROMS.xlsx) and enable automated billing (Phase 3).

Visibility: Provide real-time operational dashboards to track pending and received shipments.

1.3 Dependencies from Phase 1
Functional: The pickup_manifest bridge must be operational. Odoo fsm.order records must have itad_pickup_manifest_id and itad_bol_id populated via the Phase 1 outbox.

Technical: The ITAD Core API endpoint for creating receiving_weight_record_v3 must be stable, idempotent, and accessible.

Architectural: Strict adherence to the System of Record (SoR) boundaries defined in Phase 0 is non-negotiable.

1.4 Stakeholders & Responsible Roles (RACI)
Role / Responsibility	Vincent (Shipping/Receiving)	Odoo Dev Team	ITAD Core Dev Team	Compliance Lead	Product Owner
Requirements & UAT	A, R	C	I	C	A
Odoo UI/Model Dev	I	R, A	C	I	C
ITAD Core API Dev	I	C	R, A	I	C
Taxonomy Definition	C	C	R	A, R	A
Compliance Validation	I	C	C	R, A	A
Production Deployment	I	R	R	A	A
RACI Key: R: Responsible, A: Accountable, C: Consulted, I: Informed

2. Scope of Phase 2
2.1 Functional Scope (In-Scope)
Receiving Dashboard: An Odoo UI for Vincent to view all pickup_manifest records pending physical receipt.

Receipt Confirmation Wizard: A guided, 3-step UI to confirm receipt, select material type, and input weight, triggering the ITAD Core compliance API.

Material Taxonomy Management: A synchronized, read-only catalog of material types (stream, hazard class, billing action) from ITAD Core into Odoo.

Audit Trail: Complete logging of all receipt attempts (success/failure) within Odoo.

Billing-Ready Fields: Extension of the taxonomy model with fields for default pricing and accounting rules (default_price, basis_of_charge, gl_account_code).

2.2 Technical Scope
Odoo Model Extensions: New fields on fsm.order (itad_receipt_state). New models: itad.receiving.wizard (transient), itad.receipt.audit.log, itad.material.type.cache.

ITAD Core API Consumption: Integration with POST /api/v1/receiving-weight-records and GET /api/v1/material-types.

Synchronization Engine: A scheduled job in Odoo to pull and cache the material taxonomy from ITAD Core.

Enhanced Validation: Client-side validation for weights, BOL format, and user permissions.

2.3 Out-of-Scope Items
Automated Billing Engine: Price calculation and invoice generation (Phase 3).

Advanced Logistics: Route optimization, mobile driver app, GPS tracking (Phase 3).

Customer Self-Service Portal: Client-facing status portal (Phase 4).

Multi-Tenancy & SaaS Features: Architectural changes for a multi-tenant deployment.

AI/ML Features: Predictive scheduling or image-based classification.

3. Sub-Phases Breakdown
3.1 Phase 2.1: Receiving Dashboard MVP ✅ COMPLETE
Objective: Deliver immediate value with a simple UI for confirming receipt of manifests, validating the user workflow.

Technical Tasks:

Extend fsm.order with itad_receipt_state (pending/received/exception).

Create transient wizard itad.receiving.wizard with hardcoded material type list.

Build Receiving Dashboard tree view and form views.

Integrate wizard with ITAD Core POST /api/v1/receiving-weight-records.

Integration Points: Odoo UI → ITAD Core API (creates receiving_weight_record_v3). Status is written back to fsm.order.

Deliverables: Updated fsm_order.py, itad_receiving_wizard.py, itad_receiving_views.xml, security rules.

Entry Criteria: Phase 1 verified. ITAD Core receiving endpoint stable.

Exit Criteria: Vincent can complete the receipt workflow end-to-end. All attempts logged.

Risks & Mitigations:

Risk: Hardcoded defaults (container, scale) are inflexible. Mitigation: Document as MVP limitation; make configurable in 2.2.

Risk: No retry mechanism for API failures. Mitigation: Implement manual retry with preserved idempotency key in 2.2.

3.2 Phase 2.2: Transition Hardening 🟡 IN PROGRESS
Objective: Harden the MVP for production by addressing technical debt, improving robustness, and adding operational controls.

Technical Tasks:

Replace hardcoded defaults with configurable ir.config_parameter values.

Implement RBAC with dedicated group_receiving_manager.

Add client-side rate limiting and enhanced validation (BOL format).

Create comprehensive audit log (itad.receipt.audit.log) and archiving strategy.

Write integration contract tests and backward compatibility migration scripts.

Integration Points: Formalizes the API contract. Adds health checks to the ITAD Core integration.

Deliverables: Config parameters, enhanced wizard, audit log model, integration test suite, migration script.

Entry Criteria: Phase 2.1 code complete and tested.

Exit Criteria: All configs are system-managed, security groups are enforced, and a full audit trail exists.

Risks & Mitigations:

Risk: Complex validation slows down warehouse throughput. Mitigation: UX review with Vincent; keep validation fast and contextual.

3.3 Phase 2.3: Authoritative Material Taxonomy & Sync 🚀 NEXT
Objective: Establish ITAD Core as the System of Record for material taxonomy; implement one-way sync to Odoo.

Technical Tasks:

ITAD Core: Implement GET /api/v1/material-types endpoint.

Odoo: Create cache model itad.material.type.cache with itad_core_id as primary sync key.

Odoo: Build sync engine itad.material.sync with sync_material_types() method.

Odoo: Modify receiving wizard to use synced taxonomy (Many2one to cache).

Create admin UI for cache management and manual sync.

Integration Points: ITAD Core (SoR) → Odoo (Cache). Odoo wizard consumes cached data.

Deliverables: New ITAD Core endpoint. New Odoo models *_cache.py, *_sync.py. Updated wizard. Sync UI and cron job.

Entry Criteria: Phase 2.2 stable. Business agreement on final taxonomy structure.

Exit Criteria: Wizard uses dynamic taxonomy. Sync runs successfully on schedule. Deactivated items in ITAD Core reflect in Odoo.

Risks & Mitigations:

Risk: Initial sync failure leaves Odoo with no valid material types. Mitigation: Implement pre-flight health check and clear admin alerts. Wizard must degrade gracefully.

Risk: itad_core_id mismatches cause duplicates. Mitigation: Enforce rule: sync logic must use itad_core_id for all search()/write() operations.

3.4 Phase 2.4: Billing Foundation & Data Migration
Objective: Lay the data foundation for Phase 3 (Billing) and migrate legacy classification data.

Technical Tasks:

Extend itad.material.type.cache with billing fields (default_price, basis_of_charge, gl_account_code).

Develop and execute a validated migration script from Categories ROMS.xlsx into the ITAD Core taxonomy.

Build basic Odoo reports: "Received Weight by Material Type" and "Customer Receipt History".

Integration Points: Legacy data (spreadsheet) → ITAD Core (SoR) → Odoo Cache. Taxonomy now links directly to financial rules.

Deliverables: Enriched cache model, migration script & runbook, QWeb report views.

Entry Criteria: Phase 2.3 stable and syncing.

Exit Criteria: Legacy spreadsheet retired. Material types contain pricing metadata. Basic operational reports are available.

Risks & Mitigations:

Risk: Messy legacy data causes import corruption. Mitigation: Build a pre-validation script with dry-run mode and detailed exception reporting for manual reconciliation.

4. Data Model Changes
4.1 Odoo Models
fsm.order (Extension)

itad_receipt_state (Selection): pending, received, exception. Tracks facility receipt status.

itad.receiving.wizard (New - Transient)

material_type_id (Many2one to itad.material.type.cache): Replaces hardcoded selection.

actual_weight_lbs (Float): Confirmed weight at facility.

itad.receipt.audit.log (New)

Logs every wizard submission attempt: correlation_id, idempotency_key, user_id, fsm_order_id, request_payload, response_status, error_message.

itad.material.type.cache (New)

itad_core_id (Char, Key Field): Immutable UUID from ITAD Core.

code, name, stream, hazard_class, default_action, requires_photo, requires_weight, is_active.

last_synced_at, sync_state.

Phase 2.4 Additions: default_price (Float), basis_of_charge (Selection), gl_account_code (Char).

4.2 ITAD Core Models (Reference)
material_type (Extended)

Enhanced to include fields for sync and billing (mirroring Odoo cache).

receiving_weight_record_v3 (Consumed)

No schema changes from Phase 1. Phase 2 populates it via API.

4.3 Taxonomy & External IDs
The itad_core_id on the cache model is the canonical external ID. The external_id_map pattern from Phase 0 is followed, but encapsulated within the dedicated cache model.

Taxonomy is now a 3-level normalized structure (Group/Stream → Material Type → Attributes) managed in ITAD Core, replacing the flat Categories ROMS.xlsx.

5. Integration Design
5.1 Sync Points & Data Flow
graph TD
    A[ITAD Core: material_type] -- GET /material-types --> B[Odoo Cron: Sync Job];
    B -- Upsert by itad_core_id --> C[Odoo: material.type.cache];
    D[User: Opens Wizard] --> E[Odoo: receiving.wizard];
    C -- Provides Dropdown --> E;
    E -- POST /receiving-weight-records --> F[ITAD Core API];
    F -- Creates --> G[ITAD Core: receiving_weight_record_v3];
    F -- Returns Success --> E;
    E -- Updates State --> H[Odoo: fsm.order];
    E -- Logs Attempt --> I[Odoo: receipt.audit.log];
5.2 Idempotency & Error Handling
Idempotency Key: Generated once per wizard session (receipt-{fsm_order_id}-{timestamp}) and stored in the audit log. Reused on retries.

Retry Logic: Manual retry only (via wizard). Automatic retry is not implemented to prevent uncontrolled loops. Exponential backoff is handled by the underlying itad_outbox pattern if used.

Error Classification:

4xx (Client): Show to user, do not retry automatically (e.g., validation error).

5xx (Server)/Network: Allow manual retry with same idempotency key.

State Conflict: If itad_receipt_state is already received, block action and alert user.

5.3 Backward Compatibility
The itad_receipt_state field must be backfilled for all existing fsm.order records with a pickup_manifest_id (default: pending).

The migration script from Phase 2.2 must ensure no data loss for records in exception state.

API changes are additive; default values are supplied for new required fields in the receiving payload.

6. Validation & Testing Strategy
6.1 Test Requirements
Unit Tests: All new Odoo models and methods (wizard logic, sync engine, validation).

Integration Tests:

Wizard ↔ ITAD Core API contract (using mocks).

Taxonomy sync engine ↔ ITAD Core GET endpoint.

Audit log integrity.

Regression Tests: Phase 1 pickup_manifest submission must still work.

User Acceptance Test (UAT): Vincent must execute the full workflow with real-world data.

6.2 Compliance & Audit Checks
Traceability: Verify that every receiving_weight_record_v3 ID can be traced back to a specific itad.receipt.audit.log entry, user, and fsm.order.

Immutability: Confirm that the receiving_weight_record_v3 cannot be modified via the Odoo interface—only through ITAD Core's void/reissue workflow.

Data Integrity: Validate that the material code used in the receiving API matches an active record in the synchronized taxonomy cache.

7. Reporting & Operationalization
7.1 Initial Reports & Dashboards
Receiving Dashboard (Odoo): Primary operational tool. Filter: itad_receipt_state = 'pending'.

Material Receipt Summary (Odoo QWeb): Daily/weekly report of weight received by material stream.

Audit Log Review (Odoo): Interface for managers to review failed or exceptional receipt attempts.

7.2 Data Quality Gates
Pre-Sync Check: Taxonomy sync job must validate that >95% of active material types have required fields (code, stream, default_action) before updating the cache.

Post-Receipt Check: System flags any receipt where actual_weight_lbs deviates >50% from the pickup_manifest estimated weight for review.

7.3 KPIs & Monitoring
KPI 1: Receiving Cycle Time (Pickup arrival to digital receipt confirmation). Target: < 2 hours.

KPI 2: Receipt First-Pass Yield (% of receipt attempts that succeed without error). Target: > 95%.

Monitoring Alerts:

Taxonomy sync failure for > 24h.

5 consecutive API failures from the receiving wizard.

High rate of exception states on receipts.

8. Appendices
8.1 Glossary
Receiving Weight Record v3: The immutable compliance anchor created in ITAD Core upon physical receipt of material. Contains final weights, receiver, and timestamps.

Material Taxonomy: The hierarchical classification system for waste materials (e.g., Stream: Batteries → Type: Lithium-Ion → Attributes). SoR: ITAD Core.

Idempotency Key: A unique client-generated key sent with API requests to prevent duplicate record creation upon retries.

8.2 References
Phase 0: ITAD Data Model v0.9.pdf, SOR_LOCK.md (SoR boundaries).

Phase 1: PHASE_1_VERIFICATION_LOG.md (Integration foundation).

Business Process: ModernWaste_Phase1_Blueprint_Consolidation.docx (Roles & workflow).

8.3 Relevant Endpoints
ITAD Core:

POST /api/v1/receiving-weight-records (Payload defined in INTEGRATION_CONTRACT_ODoo_ITADCore.md)

GET /api/v1/material-types (To be implemented in Phase 2.3)

GET /health (For compatibility checks)