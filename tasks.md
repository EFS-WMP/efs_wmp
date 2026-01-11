# Phase 0 Lock Review Tracker (Canonical)

Progress Summary
- Completed: 31/31
- Current milestone: Phase 0 Lock Review complete (awaiting sign-off; keep Phase 1 blocked)
- Phase 1 remains BLOCKED pending sign-off even though items 1-31 are checked.
- SoR lock: Odoo is SoR for scheduling/work orders/day routes/dispatch execution. ITAD Core is SoR for compliance/receiving/processing/custody/evidence/reconciliation/lots/shipments/disposition/certificates/settlement. Routific is optimizer-only. Acceptance/dispatch commits to Odoo; ITAD Core receives compliance artifacts later via pickup_manifest -> BOL -> receiving...
- [ ] Enforce CODEX_CHECKLIST.md for every change set (Acceptance: PR/review must reference checklist)
- [ ] Phase 1 Pre-Start Gate: Lock Routific caller = Odoo (Acceptance: docs updated in PHASE_0.md + glossary.md + object_map.md + PHASE_0_LOCK_REVIEW gate)
- [x] Phase 1 SoR Guard Clarification: Operational-truth keys forbidden EXCEPT inside `*_snapshot_json` / `snapshot_json` (Acceptance: recursive guard with snapshot exemption implemented; tests passing)
- [x] Phase 1 Verification Gate Commands (canonical paths):
- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec -T itad-core pytest -q`
  - `docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 odoo -c /etc/odoo/odoo.conf -d <DB_NAME> -u itad_core --stop-after-init --test-enable`

### Phase 0 Step 1 — Canonical docs gate [x]
Definition / Intent:
- Ensure canonical docs under docs/phase0/ are the single source of truth and stray copies are archived.
Acceptance Criteria:
- Non-canonical docs moved to docs/phase0/archive/2026-01-02/ with archive headers (see docs-phase0-tasks.md, itad-core-tasks.md).
- Canonical docs explicitly lock the SoR wording; README/ROADMAP reference only the canonical files.
- Verification commands complete with zero contradictory hits: `rg -n "system of record for all operational data" docs/phase0` (0 matches); `rg -n "ITAD Core serves as the system of record" docs/phase0` (canonical summary only); `rg -n "acceptance.*commits to ITAD Core" docs/phase0` (0 matches); `rg -n "PHASE_0\\.md|PHASE_0_LOCK_REVIEW\\.md|glossary\\.md|object_map\\.md" -S docs/phase0` (canonical files only).
Evidence / References:
- docs/phase0/PHASE_0.md; docs/phase0/PHASE_0_LOCK_REVIEW.md; docs/phase0/glossary.md; docs/phase0/object_map.md; docs/phase0/archive/2026-01-02/ (archived variants).

### Phase 0 Step 2 — Evidence index created [x]
Definition / Intent:
- Publish a verifiable index mapping each Phase 0 checklist item to docs/schema/tests.
Acceptance Criteria:
- `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` covers A1–I30 with doc/schema/migration/test evidence and PASS statuses.
- `scripts/phase0_validate_evidence_index.py` verifies referenced paths exist.
- Verification commands:
  1. `rg -n "PASS" docs/phase0/PHASE_0_EVIDENCE_INDEX.md`
  2. `rg -n "PHASE_0_EVIDENCE_INDEX" -S docs/phase0`
  3. `python scripts/phase0_validate_evidence_index.py`
Evidence / References:
- docs/phase0/PHASE_0_EVIDENCE_INDEX.md; scripts/phase0_validate_evidence_index.py

### Phase 0 Step 3 — Verification log & runner [x]
Definition / Intent:
- Capture reproducible verification commands and store their outputs for audit.
Acceptance Criteria:
- `docs/phase0/PHASE_0_VERIFICATION_LOG.md` contains a template for summarizing verification runs.
- `scripts/phase0_verify.ps1` runs the canonical `rg` checks + evidence index validation and writes logs under `docs/phase0/verification_runs/`.
- Verification commands:
  1. `powershell -ExecutionPolicy Bypass -File scripts/phase0_verify.ps1`
  2. `rg -n "Phase 0 Verification Log" docs/phase0/PHASE_0_VERIFICATION_LOG.md`
Evidence / References:
- docs/phase0/PHASE_0_VERIFICATION_LOG.md; scripts/phase0_verify.ps1; docs/phase0/verification_runs/2026-01-02_2112.txt

### Phase 0 Step 4 — Tracking canonicalization verified [x]
Definition / Intent:
- Confirm only the canonical tracker (`tasks.md`) and checklist (`docs/phase0/PHASE_0_LOCK_REVIEW.md`) remain active and referenced.
Acceptance Criteria:
- README.md, docs/ROADMAP.md, and other docs reference only `tasks.md` and `docs/phase0/PHASE_0_LOCK_REVIEW.md`.
- Verification command: `rg -n "tasks\.md|PHASE_0_LOCK_REVIEW\.md" README.md docs/ROADMAP.md docs -S`
Evidence / References:
- README.md; docs/ROADMAP.md; command output ensures canonical references.

### Phase 0 Step 5 — SoR Guardrails enforced [x]
Definition / Intent:
- Prevent contradictory SoR language from reappearing in the canonical docs.
Acceptance Criteria:
- `docs/phase0/SOR_LOCK.md` records the locked statement plus forbidden examples.
- `scripts/phase0_sor_guard.ps1` runs canonical `rg` probes and fails if the SoR lock is missing or forbidden phrases appear.
- Verification command:
  `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1`
Evidence / References:
- docs/phase0/SOR_LOCK.md; scripts/phase0_sor_guard.ps1; README.md (SoR Guardrails section).

### Phase 0 Step 6 ƒ?" Evidence Index PASS + verification run recorded [x]
Definition / Intent:
- Verify every Phase 0 checklist item has documented evidence and capture a reproducible verification run that covers migrations, tests, seed data, and SoR guard checks.
Acceptance Criteria:
- `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` lists all A–I items as PASS with doc/schema/migration/test/seed evidence links.
- `docs/phase0/PHASE_0_VERIFICATION_LOG.md` records the latest run with the `alembic`, `pytest`, `seed_demo`, guard, validator, and grep outputs.
- Verification commands executed:
 1. `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core alembic upgrade head`
 2. `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m pytest -q`
 3. `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m app.scripts.seed_demo`
  4. `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1`
  5. `python scripts/phase0_validate_evidence_index.py`
  6. `rg -n "\| (PARTIAL|FAIL) \|" docs/phase0/PHASE_0_EVIDENCE_INDEX.md`
Evidence / References:
- docs/phase0/PHASE_0_EVIDENCE_INDEX.md
- docs/phase0/PHASE_0_VERIFICATION_LOG.md
- scripts/phase0_verify.ps1
- scripts/phase0_sor_guard.ps1
- scripts/phase0_validate_evidence_index.py
- docs/phase0/PHASE_0_LOCK_REVIEW.md

### Phase 0 Step 7 — Closure Pack assembled; Phase 0 CLOSED [x]
Definition / Intent:
- Assemble the closure pack (summary, risks, readiness gate) and keep Phase 1 blocked until the readiness gate reports PASS.
Acceptance Criteria:
- `docs/phase0/PHASE_0_SIGNOFF_SUMMARY.md`, `docs/phase0/PHASE_0_RISK_REGISTER.md`, and `docs/phase0/PHASE_1_READINESS_GATE.md` exist and the Sign-off Bundle references them.
- Canonical docs no longer reference `docs/phase0/archive/` (`rg -n "archive/" docs/phase0 -S` must return 0 hits).
- Phase 1 remains BLOCKED until the readiness gate confirms PASS; manifest/implementation_plan mention the readiness gate as the unlock control.
Verification Commands:
  1. `rg -n "archive/" docs/phase0 -S`
  2. `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1`
  3. Confirm the closure pack docs exist under `docs/phase0/`.
Evidence / References:
- `docs/phase0/PHASE_0_SIGNOFF_SUMMARY.md`
- `docs/phase0/PHASE_0_RISK_REGISTER.md`
- `docs/phase0/PHASE_1_READINESS_GATE.md`
- `docs/phase0/PHASE_0_LOCK_REVIEW.md` (Sign-off Bundle)

## A) Architecture & Ownership (Items 1-4)

### 1. System Boundaries & Ownership (Odoo vs ITAD Core vs Routific) [x]
Definition / Intent:
- Define unambiguous SoR boundaries and single-writer ownership.
Acceptance Criteria:
- SoR statement and ownership matrix documented.
- Single-writer principle stated and non-conflicting.
Evidence / References:
- docs/phase0/PHASE_0.md (System Boundaries & Ownership)
- docs/phase0/PHASE_0_LOCK_REVIEW.md (A1)

### 2. Routific is optimizer-only (not SoR) [x]
Definition / Intent:
- Ensure optimization proposals never become operational truth.
Acceptance Criteria:
- Routific described as advisory-only with no write-back.
- Storage and retention policy described.
Evidence / References:
- docs/phase0/PHASE_0_LOCK_REVIEW.md (A2)
- docs/phase0/PHASE_0.md (System Boundaries & Ownership)

### 3. Glossary exists with required terms [x]
Definition / Intent:
- Provide consistent vocabulary for Phase 0 artifacts.
Acceptance Criteria:
- Glossary includes BOL, Receiving Anchor, Workstream, Lot, LPN, Disposition, Settlement, Pickup Manifest.
Evidence / References:
- docs/phase0/glossary.md
- docs/phase0/PHASE_0_LOCK_REVIEW.md (A3)

### 4. Canonical object map exists (end-to-end chain) [x]
Definition / Intent:
- Define canonical object flow from planning to settlement.
Acceptance Criteria:
- Object map includes Pickup Plan -> Occurrence -> Day Route -> Pickup Manifest -> BOL -> Receiving -> Processing -> Lots -> Shipments -> Disposition -> Settlement.
Evidence / References:
- docs/phase0/object_map.md
- docs/phase0/PHASE_0_LOCK_REVIEW.md (A4)

## B) Identifiers & Versioning (Items 5-8)

### 5. BOL# global uniqueness rule + rationale [x]
Definition / Intent:
- Enforce globally unique bol_number for compliance and integration.
Acceptance Criteria:
- DB unique constraint on bol_number.
- Duplicate create returns 409.
Evidence / References:
- itad-core/app/models/bol.py
- itad-core/app/api/v1/bol.py
- docs/phase0/PHASE_0.md (B1)

### 6. ID/key format policy defined [x]
Definition / Intent:
- Standardize UUID usage and human-readable IDs.
Acceptance Criteria:
- UUID v4 used for primary keys.
- BOL number format documented and auto-generated when omitted.
Evidence / References:
- itad-core/app/services/bol_service.py
- docs/phase0/PHASE_0.md (B2)

### 7. External IDs strategy (odoo_*, routific_*) [x]
Definition / Intent:
- Map external system IDs without violating SoR boundaries.
Acceptance Criteria:
- external_id_map schema exists with unique constraint.
- Strategy documented.
Evidence / References:
- itad-core/app/models/external_ids.py
- docs/phase0/PHASE_0.md (B3)

### 8. Customer requirement profiles versioned + snapshot at intake [x]
Definition / Intent:
- Capture immutable requirements at BOL creation.
Acceptance Criteria:
- requirement_profile_* fields present in schema.
- Snapshot documented.
Evidence / References:
- itad-core/app/schemas/bol.py
- docs/phase0/PHASE_0.md (B4)

## C) Workflow (Gates, Stages, Closure) (Items 9-12)

### 9. GATE_TYPE list + append-only rule for bol_stage_gates [x]
Definition / Intent:
- Ensure lifecycle transitions are standardized and immutable.
Acceptance Criteria:
- Gate types defined and validated.
- Append-only rule documented.
Evidence / References:
- itad-core/app/models/bol_stage_gates.py
- docs/phase0/PHASE_0.md (C1-C2)

### 10. Gate transition matrix for BOL + workstream lifecycle [x]
Definition / Intent:
- Prevent invalid state transitions.
Acceptance Criteria:
- Transition matrix implemented in service logic.
- Invalid transitions rejected.
Evidence / References:
- itad-core/app/services/bol_service.py
- docs/phase0/PHASE_0.md (C3)

### 11. Two-level closure (workstream close -> BOL close) [x]
Definition / Intent:
- Ensure processing completion before BOL closure.
Acceptance Criteria:
- BOL close blocked until required workstreams complete.
- Closure rules documented.
Evidence / References:
- itad-core/app/services/bol_service.py
- docs/phase0/PHASE_0.md (C4)

### 12. "What is required to close" mechanism defined [x]
Definition / Intent:
- Define required processing flags that gate closure.
Acceptance Criteria:
- requires_* fields exist and are locked by confirmation.
- Source documented.
Evidence / References:
- itad-core/app/models/bol.py
- docs/phase0/PHASE_0.md (C5)

## D) Receiving Anchor (Immutable) (Items 13-16)

### 13. Receiving Weight Record v3 required fields [x]
Definition / Intent:
- Ensure complete compliance capture at receiving.
Acceptance Criteria:
- Required fields enforced by schema/DB constraints.
- Missing required fields return 422.
Evidence / References:
- itad-core/app/schemas/receiving.py
- itad-core/alembic/versions/0004_phase0_d.sqlalchemy.py
- docs/phase0/PHASE_0.md (D1)

### 14. Receiving record immutability (void/reissue only) [x]
Definition / Intent:
- Prevent updates to immutable receiving anchors.
Acceptance Criteria:
- No update/delete endpoints.
- Void and reissue endpoints implemented.
Evidence / References:
- itad-core/app/api/v1/receiving.py
- itad-core/app/services/receiving_service.py
- docs/phase0/PHASE_0.md (D2)

### 15. tare_source policy + ban average tare [x]
Definition / Intent:
- Require valid tare sources and snapshots.
Acceptance Criteria:
- Allowed tare_source list enforced.
- Snapshot JSON required for snapshot sources.
Evidence / References:
- itad-core/app/services/receiving_service.py
- itad-core/alembic/versions/0005_phase0_d_receiving_constraints.sqlalchemy.py
- docs/phase0/PHASE_0.md (D3)

### 16. Blind Receiving mode defined and enforced [x]
Definition / Intent:
- Hide declared weights from receiving staff unless authorized.
Acceptance Criteria:
- Declared weights redacted by default in blind mode.
- Admin include_declared gate enforced.
Evidence / References:
- itad-core/app/api/v1/receiving.py
- docs/phase0/PHASE_0.md (D4)

## E) Processing Domains & Taxonomy (Items 17-20)

### 17. Battery and E-waste domains as session+lines, configurable catalogs [x]
Definition / Intent:
- Model processing as sessions with taxonomy-backed line items.
Acceptance Criteria:
- battery_processing_session/line and ewaste_processing_session/line tables + APIs exist.
- Session create/GET return lines; demo data seeded.
Evidence / References:
- itad-core/app/models/processing.py; itad-core/app/api/v1/processing.py; itad-core/app/services/processing_service.py
- itad-core/alembic/versions/0006_phase0_e_taxonomy_processing.sqlalchemy.py
- itad-core/tests/test_processing_taxonomy.py
- itad-core/app/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (E1)

### 18. HARD RULE: line items must reference taxonomy_item_id [x]
Definition / Intent:
- Eliminate free-text processing categories; enforce taxonomy linkage.
Acceptance Criteria:
- Request schemas require taxonomy_item_id; no free-text category fields; missing taxonomy_item_id returns 422.
Evidence / References:
- itad-core/app/schemas/processing.py
- itad-core/tests/test_processing_taxonomy.py
- docs/phase0/PHASE_0.md (E2)

### 19. Taxonomy 3-level defined + governance policy [x]
Definition / Intent:
- Group/Type/Variant taxonomy with effective dating and change log; no deletions or in-place code renames.
Acceptance Criteria:
- taxonomy_type/taxonomy_item tables with effective_from/ effective_to/is_active; taxonomy_change_log append-only; no DELETE endpoints.
Evidence / References:
- itad-core/app/models/taxonomy.py; itad-core/app/api/v1/taxonomy.py; itad-core/app/services/taxonomy_service.py
- itad-core/alembic/versions/0006_phase0_e_taxonomy_processing.sqlalchemy.py
- itad-core/tests/test_processing_taxonomy.py
- docs/phase0/PHASE_0.md (E3); docs/phase0/PHASE_0_LOCK_REVIEW.md

### 20. SB20/non-SB20 attributes defined at taxonomy level [x]
Definition / Intent:
- Provide SB20 flag on taxonomy items for reporting and filtering.
Acceptance Criteria:
- sb20_flag stored on taxonomy_item; GET items supports sb20_flag filter; seed/demo includes SB20 and non-SB20 variants.
Evidence / References:
- itad-core/app/models/taxonomy.py; itad-core/app/api/v1/taxonomy.py
- itad-core/tests/test_processing_taxonomy.py
- itad-core/app/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (E4)

## F) Reconciliation & Disputes (Items 21-23)

### 21. Reconciliation model defined (variance, pct, threshold) + approval requirement [x]
Definition / Intent:
- Append-only reconciliation runs per BOL with variance calc, thresholds, and approval-required flag.
Acceptance Criteria:
- reconciliation_run table with run_no per BOL, variance fields, thresholds, nonnegative checks; change log not needed here; creation logic in repo.
Evidence / References:
- itad-core/app/models/reconciliation.py; itad-core/app/repositories/reconciliation_repo.py
- itad-core/alembic/versions/0007_phase0_f_reconciliation_disputes.sqlalchemy.py
- itad-core/tests/test_phase0_f_reconciliation_disputes_data_layer.py
- itad-core/app/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (F1); docs/phase0/PHASE_0_LOCK_REVIEW.md

### 22. BOL closure blocked if variance > threshold without reason+approver [x]
Definition / Intent:
- Over-threshold reconciliation requires explicit approval; otherwise closure blocked.
Acceptance Criteria:
- Effective status derived from latest run + approval event; blockers return RECONCILIATION_OVER_THRESHOLD until APPROVE.
Evidence / References:
- itad-core/app/repositories/reconciliation_repo.py
- itad-core/tests/test_phase0_f_reconciliation_disputes_data_layer.py
- itad-core/app/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (F2); docs/phase0/PHASE_0_LOCK_REVIEW.md

### 23. Discrete discrepancy workflow exists and blocks closure [x]
Definition / Intent:
- Track disputes as discrepancy_case with explicit states; open disputes block closure until resolved/voided.
Acceptance Criteria:
- discrepancy_case table with case_no per BOL; repo enforces state transitions; blockers return DISPUTE_OPEN until resolved.
Evidence / References:
- itad-core/app/models/reconciliation.py; itad-core/app/repositories/discrepancy_repo.py
- itad-core/alembic/versions/0007_phase0_f_reconciliation_disputes.sqlalchemy.py
- itad-core/tests/test_phase0_f_reconciliation_disputes_data_layer.py
- itad-core/app/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (F3); docs/phase0/PHASE_0_LOCK_REVIEW.md

## G) Evidence & Chain of Custody (Items 24-26)

### 24. Evidence artifacts layer defined (types, hash, storage refs, visibility) [x]
Definition / Intent:
- Immutable artifacts with content-addressed sha256, storage pointers, retention, and visibility controls.
Acceptance Criteria:
- evidence_artifact table with sha format/unique constraints; repo validates sha; dedup/idempotent create; tests cover uniqueness/validation.
Evidence / References:
- itad-core/app/models/evidence.py; itad-core/app/repositories/artifacts_repo.py
- itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py
- itad-core/tests/test_phase0_g_evidence_custody_data_layer.py
- docs/phase0/PHASE_0.md (G1); docs/phase0/PHASE_0_LOCK_REVIEW.md

### 25. artifact_links structure exists [x]
Definition / Intent:
- Generic artifact links to entities with roles and optional visibility override.
Acceptance Criteria:
- artifact_link table with UNIQUE(artifact_id, entity_type, entity_id, link_role); repo enforces allowed entity_type; visibility rules enforced when listing.
Evidence / References:
- itad-core/app/models/evidence.py; itad-core/app/repositories/artifacts_repo.py
- itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py
- itad-core/tests/test_phase0_g_evidence_custody_data_layer.py
- docs/phase0/PHASE_0.md (G2); docs/phase0/PHASE_0_LOCK_REVIEW.md

### 26. Chain of Custody append-only policy defined [x]
Definition / Intent:
- Append-only custody events for moves/scans; corrections via compensating events.
Acceptance Criteria:
- custody_event table with timeline ordering; repo adds events and supports supersedes_event_id; tests ensure append-only and compensating linkage.
Evidence / References:
- itad-core/app/models/evidence.py; itad-core/app/repositories/custody_repo.py
- itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py
- itad-core/tests/test_phase0_g_evidence_custody_data_layer.py
- itad-core/app/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (G3); docs/phase0/PHASE_0_LOCK_REVIEW.md

## F) Reconciliation & Disputes (Items 21-23)

### 21. Reconciliation model defined (variance, pct, threshold) [x]
Definition / Intent:
- Define variance rules and approval thresholds.
Acceptance Criteria:
- reconciliation_run with variance_lbs/pct, thresholds, approval_required flag; append-only run_no per BOL; nonnegative checks.
Evidence / References:
- itad-core/app/models/reconciliation.py; itad-core/app/repositories/reconciliation_repo.py
- itad-core/alembic/versions/0007_phase0_f_reconciliation_disputes.sqlalchemy.py
- itad-core/tests/test_phase0_f_reconciliation_disputes_data_layer.py
- docs/phase0/PHASE_0.md (F section); docs/phase0/PHASE_0_LOCK_REVIEW.md (F)

### 22. BOL closure blocked if variance > threshold [x]
Definition / Intent:
- Prevent closure without approved variance resolution.
Acceptance Criteria:
- Effective status derived from reconciliation_run + reconciliation_approval_event; over-threshold without APPROVE is a blocker.
Evidence / References:
- itad-core/app/repositories/reconciliation_repo.py (bol_close_blockers)
- docs/phase0/PHASE_0.md (F section); docs/phase0/PHASE_0_LOCK_REVIEW.md (F)

### 23. Discrete discrepancy workflow exists and blocks closure [x]
Definition / Intent:
- Track disputes and required artifacts before closing.
Acceptance Criteria:
- discrepancy_case with OPEN/IN_DISPUTE/RESOLVED/VOIDED; resolution requires resolved_by/text; open cases block closure.
Evidence / References:
- itad-core/app/models/discrepancy.py; itad-core/app/repositories/discrepancy_repo.py
- itad-core/tests/test_phase0_f_reconciliation_disputes_data_layer.py
- docs/phase0/PHASE_0.md (F section); docs/phase0/PHASE_0_LOCK_REVIEW.md (F)

## G) Evidence & Chain of Custody (Items 24-26)

### 24. Evidence artifacts layer defined [x]
Definition / Intent:
- Define artifact types, hashes, and storage references.
Acceptance Criteria:
- evidence_artifact schema with sha256 format check, unique content pointer, visibility and metadata.
Evidence / References:
- itad-core/app/models/evidence.py; itad-core/app/repositories/artifacts_repo.py
- itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py
- itad-core/tests/test_phase0_g_evidence_custody_data_layer.py
- docs/phase0/PHASE_0.md (G section); docs/phase0/PHASE_0_LOCK_REVIEW.md (G)

### 25. artifact_links structure exists [x]
Definition / Intent:
- Link artifacts to BOL/receiving/sessions/lots/shipments/disposition/settlement.
Acceptance Criteria:
- artifact_link unique per artifact/entity/role; allowed entity_type enforced; visibility override supported.
Evidence / References:
- itad-core/app/models/evidence.py; itad-core/app/repositories/artifacts_repo.py
- itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py
- itad-core/tests/test_phase0_g_evidence_custody_data_layer.py
- docs/phase0/PHASE_0.md (G section); docs/phase0/PHASE_0_LOCK_REVIEW.md (G)

### 26. Chain of Custody append-only defined [x]
Definition / Intent:
- Ensure custody events are immutable with compensating fixes only.
Acceptance Criteria:
- custody_event model append-only; supersedes_event_id supports compensating events; timeline ordered by occurred_at.
Evidence / References:
- itad-core/app/models/evidence.py; itad-core/app/repositories/custody_repo.py
- itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py
- itad-core/tests/test_phase0_g_evidence_custody_data_layer.py
- itad-core/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (G section); docs/phase0/PHASE_0_LOCK_REVIEW.md (G)

## H) Inventory, Outbound, Downstream (Items 27-29)

### 27. LPN/container instances + locations + lots model exists [x]
Definition / Intent:
- Track inventory with locations and statuses.
Acceptance Criteria:
- warehouse_location, lpn_container, inventory_lot, lot_lpn_membership tables with unique codes; statuses WIP/READY/SHIPPED/QUARANTINE; lot membership append-only; custody_event used for moves.
Evidence / References:
- itad-core/app/models/inventory.py; itad-core/app/repositories/inventory_repo.py
- itad-core/alembic/versions/0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py
- itad-core/tests/test_phase0_h_inventory_outbound_downstream_data_layer.py
- itad-core/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (H section); docs/phase0/PHASE_0_LOCK_REVIEW.md (H); docs/phase0/object_map.md

### 28. Outbound shipments domain defined [x]
Definition / Intent:
- Capture outbound carrier/appointment/seals/hazmat/doc artifacts.
Acceptance Criteria:
- outbound_shipment + shipment_lpn tables; QUARANTINE LPN blocked from loading; dispatch sets LPN status SHIPPED and writes custody_event SHIP; artifacts linked via artifact_link.
Evidence / References:
- itad-core/app/models/inventory.py; itad-core/app/repositories/outbound_repo.py
- itad-core/alembic/versions/0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py
- itad-core/tests/test_phase0_h_inventory_outbound_downstream_data_layer.py
- itad-core/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (H section); docs/phase0/PHASE_0_LOCK_REVIEW.md (H)

### 29. Downstream qualification + disposition chain defined [x]
Definition / Intent:
- Define vendor allowlists and downstream proof chain.
Acceptance Criteria:
- downstream_vendor + vendor_certification versioned with allowlist flag; disposition_record requires vendor qualification and final_proof_artifact_id; proof stored as evidence_artifact.
Evidence / References:
- itad-core/app/models/inventory.py; itad-core/app/repositories/downstream_repo.py
- itad-core/alembic/versions/0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py
- itad-core/tests/test_phase0_h_inventory_outbound_downstream_data_layer.py
- itad-core/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (H section); docs/phase0/PHASE_0_LOCK_REVIEW.md (H); docs/phase0/object_map.md

## I) Variant A Integrations (Must-have) (Item 30)

### 30.1 Canonical IDs & external refs between Odoo and ITAD Core [x]
Definition / Intent:
- Lock external refs (odoo_stop_id/route/work_order) as immutable link fields while keeping ITAD Core as SoR.
Acceptance Criteria:
- pickup_manifest stores immutable Odoo refs; manifest_no unique; external refs not rewritten after creation.
Evidence / References:
- itad-core/app/models/pickup_manifest.py
- docs/phase0/PHASE_0.md (I1/I2); docs/phase0/object_map.md (Pickup Manifest)

### 30.2 Manifest state machine DRAFT -> SUBMITTED -> BOUND_TO_BOL -> RECEIVED -> CLOSED; VOIDED terminal [x]
Definition / Intent:
- Enforce strict lifecycle with append-only events.
Acceptance Criteria:
- pickup_manifest status check constraint; pickup_manifest_state_event append-only; transition_manifest_status rejects invalid moves and requires void reason.
Evidence / References:
- itad-core/app/repositories/pickup_manifest_repo.py
- itad-core/tests/test_phase0_i_pickup_manifest_bridge_data_layer.py
- docs/phase0/PHASE_0.md (I1)

### 30.3 Idempotency & retry safety (fingerprint/hash; duplicate detection rules) [x]
Definition / Intent:
- Prevent duplicate manifests under retries and require Idempotency-Key header.
Acceptance Criteria:
- UNIQUE(source_system, manifest_fingerprint); Idempotency-Key required in POST; duplicate payload returns existing manifest and logs DUPLICATE_RETURNED attempt.
Evidence / References:
- itad-core/app/models/pickup_manifest.py; itad-core/app/repositories/pickup_manifest_repo.py
- itad-core/tests/test_phase0_i_pickup_manifest_bridge_data_layer.py::test_manifest_fingerprint_deduplicates_and_attempt_logs

### 30.4 Evidence/POD handling policy (refs + hashes; immutable, append-only) [x]
Definition / Intent:
- Capture POD evidence hashes/refs without mutating history; artifacts will link via artifact_link.
Acceptance Criteria:
- pod_evidence_json stored on pickup_manifest; no delete/update path; visibility aligns to artifact rules.
Evidence / References:
- itad-core/app/models/pickup_manifest.py; itad-core/scripts/seed_demo.py
- docs/phase0/PHASE_0.md (I3); docs/phase0/glossary.md (POD Evidence)

### 30.5 BOL binding rule for PICKUP (1 manifest -> 1 BOL) [x]
Definition / Intent:
- Ensure pickup-derived BOLs are bound to exactly one manifest.
Acceptance Criteria:
- bol.pickup_manifest_id FK + unique index; bind_manifest_to_bol enforces source_type=PICKUP and required status; invariant check returns empty when bound.
Evidence / References:
- itad-core/app/models/bol.py; itad-core/app/repositories/pickup_manifest_repo.py
- itad-core/tests/test_phase0_i_pickup_manifest_bridge_data_layer.py::test_binding_requires_pickup_bol_and_submitted_status

### 30.6 Geocode confidence gating + caching/versioning per address [x]
Definition / Intent:
- Prevent floating coordinates; gate routing quality.
Acceptance Criteria:
- geocode_cache effective-dated with UNIQUE(address_hash, effective_from); geocode_gate thresholds (>=0.85 AUTO_ACCEPT, 0.60-0.85 NEEDS_REVIEW, <0.60 MANUAL_REQUIRED); attach_geocode_snapshot_to_manifest copies snapshot and sets gate.
Evidence / References:
- itad-core/app/models/pickup_manifest.py; itad-core/app/repositories/geocode_repo.py
- itad-core/tests/test_phase0_i_pickup_manifest_bridge_data_layer.py::test_geocode_gate_and_versioning, ::test_attach_geocode_snapshot_and_missing_cache
- docs/phase0/PHASE_0.md (I4); docs/phase0/glossary.md (Geocode Cache)

### 30.7 Failure modes + observability (attempt logs, correlation ids) [x]
Definition / Intent:
- Always log inbound attempts and outcomes for support/debug; capture correlation_id/idempotency_key.
Acceptance Criteria:
- pickup_manifest_integration_attempt append-only with outcome and correlation_id; transition events logged; duplicate detection recorded.
Evidence / References:
- itad-core/app/models/pickup_manifest.py; itad-core/app/repositories/pickup_manifest_repo.py
- itad-core/tests/test_phase0_i_pickup_manifest_bridge_data_layer.py::test_manifest_fingerprint_deduplicates_and_attempt_logs
- docs/phase0/PHASE_0.md (I5)

## J) Commercials & Tier Pricing Addendum (Item 31)

### 31.1 Customer Pricing Profile fields + effective dating + approval locked [x]
Definition / Intent:
- Store immutable references to Odoo pricing objects with hashes; ITAD Core not authoring pricing.
Acceptance Criteria:
- pricing_external_ref records ref_type, Odoo ids, ref_hash_sha256, effective_from/to, approvals metadata; UNIQUE per ref + effective_from.
Evidence / References:
- itad-core/app/models/pricing.py; itad-core/app/repositories/pricing_repo.py; itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py
- docs/phase0/PHASE_0.md (J1); docs/phase0/PHASE_0_LOCK_REVIEW.md (J1); docs/phase0/glossary.md (Pricing External Ref)

### 31.2 Service catalog / charge types locked (placeholders) [x]
Definition / Intent:
- Catalog authored in Odoo; ITAD Core stores references and snapshots only.
Acceptance Criteria:
- pricing_external_ref supports SERVICE_CATALOG; settlement_pricing_snapshot.pricing_payload_json captures catalog/charge metadata.
Evidence / References:
- itad-core/app/models/pricing.py; itad-core/app/models/settlement.py; docs/phase0/PHASE_0.md (J2)

### 31.3 Rule precedence locked (doc/metadata) [x]
Definition / Intent:
- Precedence documented and snapshotted; ITAD Core does not evaluate rules in Phase 0.
Acceptance Criteria:
- pricing_payload_json stores precedence metadata; snapshot_hash covers it; no rule authoring in ITAD Core.
Evidence / References:
- itad-core/app/models/settlement.py; itad-core/app/repositories/settlement_repo.py; docs/phase0/PHASE_0.md (J3)

### 31.4 Rate card versioning + settlement pricing snapshot locked [x]
Definition / Intent:
- Settlement uses append-only pricing snapshots referencing Odoo rate card versions.
Acceptance Criteria:
- settlement_pricing_snapshot UNIQUE(settlement_id, snapshot_no) with snapshot_hash_sha256; references pricing_external_ref rows; recomputation creates new snapshot_no.
Evidence / References:
- itad-core/app/models/settlement.py; itad-core/app/repositories/settlement_repo.py; itad-core/tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py

### 31.5 Basis-of-charge mapping (facts → qty) locked [x]
Definition / Intent:
- Capture computed bases used for pricing for audit.
Acceptance Criteria:
- basis_of_charge_json stored in settlement_pricing_snapshot; included in snapshot hash; tests verify deterministic hash.
Evidence / References:
- itad-core/app/models/settlement.py; itad-core/app/repositories/settlement_repo.py; itad-core/tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py

### 31.6 Manual adjustments controls (reason/approver/append-only) locked [x]
Definition / Intent:
- Adjustments are append-only events requiring reason and approver; never mutate snapshot.
Acceptance Criteria:
- settlement_adjustment_event requires reason_text + approver; append-only; compute_settlement_total sums snapshot + adjustments; tests enforce validation.
Evidence / References:
- itad-core/app/models/settlement.py; itad-core/app/repositories/settlement_repo.py; itad-core/tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py

### 31.7 Odoo ↔ ITAD Core pricing exchange policy locked (external ids + hashes) [x]
Definition / Intent:
- Pricing exchange uses immutable external ids/hashes; authoring remains in Odoo.
Acceptance Criteria:
- pricing_external_ref ref_hash_sha256; settlement snapshot hash computed deterministically; integration policy documented; no deletes.
Evidence / References:
- itad-core/app/models/pricing.py; itad-core/app/models/settlement.py; docs/phase0/PHASE_0.md (J7); docs/phase0/PHASE_0_LOCK_REVIEW.md (J7)

## Next Execution Order
- All Phase 0 sections checked. Phase 1 remains BLOCKED until formal sign-off; use CODEX_CHECKLIST.md for every change set.
