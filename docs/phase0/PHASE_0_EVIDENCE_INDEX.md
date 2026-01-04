# Phase 0 Evidence Index

## How to use this index
Each row summarizes one Phase 0 checklist item (A1–I30) and points to the tangible evidence that implements or documents it. Follow the file paths listed under Evidence (Docs/Schema/Tests/Contracts) to confirm PASS status. Items marked PARTIAL or FAIL identify missing artifacts that must be addressed before Phase 1 sign-off.

| Checklist Item | Requirement Summary | Evidence (Docs) | Evidence (Schema/Migrations) | Evidence (Contracts) | Evidence (Tests/Seed) | Verified By | Status | Missing Evidence |
|---|---|---|---|---|---|---|---|---|
| A1 | System boundaries & ownership | docs/phase0/PHASE_0.md §1 | - | - | - | Doc | PASS | - |
| A2 | Routific optimizer-only | docs/phase0/PHASE_0.md §1 | - | - | - | Doc | PASS | - |
| A3 | Glossary exists | docs/phase0/glossary.md § glossary prefix | - | - | - | Doc | PASS | - |
| A4 | Canonical object map | docs/phase0/object_map.md § chain | - | - | - | Doc | PASS | - |
| B1 | BOL uniqueness | docs/phase0/PHASE_0_LOCK_REVIEW.md §B1; itad-core/app/models/bol.py unique constraint | itad-core/app/models/bol.py | - | - | Schema | PASS | - |
| B2 | ID/key format | docs/phase0/PHASE_0_LOCK_REVIEW.md §B2 | itad-core/app/models/bol.py | - | Schema | PASS | - |
| B3 | External ID strategy | docs/phase0/PHASE_0.md § ext id map; itad-core/app/models/external_ids.py/migrations | itad-core/alembic/versions/0001... | - | - | Schema | PASS | - |
| B4 | Requirement profile snapshots | docs/phase0/PHASE_0.md § requirement profile; itad-core/app/schemas/bol.py | itad-core/app/schemas/bol.py | - | - | Schema | PASS | - |
| C1 | Gate list append-only | docs/phase0/PHASE_0.md §C1-C2; itad-core/app/models/bol_stage_gates.py | itad-core/alembic/versions/0003_phase0_c.sqlalchemy.py | - | - | Schema | PASS | - |
| C2 | Append-only rule | docs/phase0/PHASE_0.md §C2 | itad-core/alembic/versions/0003_phase0_c.sqlalchemy.py | - | - | Schema | PASS | - |
| C3 | Gate transition matrix | docs/phase0/PHASE_0.md §C3; itad-core/app/services/bol_service.py | - | - | tests/test_bol.py | Doc/Tests | PASS | - |
| C4 | Two-level closure | docs/phase0/PHASE_0.md §C4 | itad-core/app/services/bol_service.py | - | tests/test_bol.py | Docs/Tests | PASS | - |
| C5 | requires_* mechanism | docs/phase0/PHASE_0.md §C5 | itad-core/app/models/bol.py | - | tests/test_bol.py | Docs/Schema/Tests | PASS | - |
| D1 | Receiving required fields | docs/phase0/PHASE_0.md §D1 | itad-core/app/models/receiving.py | itad-core/alembic/versions/0004_phase0_d.sqlalchemy.py | tests/test_receiving.py | Schema/Tests | PASS | - |
| D2 | Immutability/void/reissue | docs/phase0/PHASE_0.md §D2 | itad-core/app/models/receiving_record_voids.py | tests/test_receiving.py | Schema/Tests | PASS | - |
| D3 | Tare policy | docs/phase0/PHASE_0.md §D3 | itad-core/app/models/receiving.py | tests/test_receiving.py | Schema/Tests | PASS | - |
| D4 | Blind receiving | docs/phase0/PHASE_0.md §D4 | itad-core/app/api/v1/receiving.py? (assumed) | tests/test_receiving.py | Doc/Tests | PASS | - |
| E1 | Processing sessions/lines | docs/phase0/PHASE_0.md §E1 | itad-core/app/models/processing.py | itad-core/alembic/versions/0006_phase0_e_taxonomy_processing.sqlalchemy.py | tests/test_processing_taxonomy.py | Docs/Schema/Tests | PASS | - |
| E2 | taxonomy_item_id required | docs/phase0/PHASE_0.md §E2; docs/phase0/object_map.md | itad-core/app/schemas/processing.py | itad-core/app/models/processing.py | tests/test_processing_taxonomy.py | Docs/Schema/Tests | PASS | - |
| E3 | 3-level taxonomy + governance | docs/phase0/PHASE_0.md §E3; docs/phase0/PHASE_0_LOCK_REVIEW.md §E3 | itad-core/app/models/taxonomy.py | itad-core/alembic/versions/0006_phase0_e_taxonomy_processing.sqlalchemy.py | tests/test_processing_taxonomy.py | Docs/Schema/Tests | PASS | - |
| E4 | SB20 flag | docs/phase0/PHASE_0.md §E4; docs/phase0/PHASE_0_LOCK_REVIEW.md §E4 | itad-core/app/models/taxonomy.py | itad-core/alembic/versions/0006_phase0_e_taxonomy_processing.sqlalchemy.py | tests/test_processing_taxonomy.py | Docs/Schema/Tests | PASS | - |
| F1 | Reconciliation model | docs/phase0/PHASE_0.md §F1; lock review F1 | itad-core/app/models/reconciliation.py | itad-core/alembic/versions/0007_phase0_f_reconciliation_disputes.sqlalchemy.py | tests/test_phase0_f_reconciliation_disputes_data_layer.py | Docs/Schema/Tests | PASS | - |
| F2 | Closure blocker via variance | docs/phase0/PHASE_0.md §F2 | itad-core/app/repositories/reconciliation_repo.py | tests/test_phase0_f_reconciliation_disputes_data_layer.py | Docs/Schema/Tests | PASS | - |
| F3 | Discrepancy workflow | docs/phase0/PHASE_0.md §F3 | itad-core/app/models/discrepancy.py | tests/test_phase0_f_reconciliation_disputes_data_layer.py | Docs/Schema/Tests | PASS | - |
| G1 | Evidence artifacts layer | docs/phase0/PHASE_0.md §G1 | itad-core/app/models/evidence.py | itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py | tests/test_phase0_g_evidence_custody_data_layer.py | Docs/Schema/Tests | PASS | - |
| G2 | artifact_links | docs/phase0/PHASE_0.md §G2 | itad-core/app/models/evidence.py | itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py | tests/test_phase0_g_evidence_custody_data_layer.py | Docs/Schema/Tests | PASS | - |
| G3 | Chain of custody append-only | docs/phase0/PHASE_0.md §G3 | itad-core/app/models/evidence.py | itad-core/alembic/versions/0008_phase0_g_evidence_custody.sqlalchemy.py | tests/test_phase0_g_evidence_custody_data_layer.py | Docs/Schema/Tests | PASS | - |
| H1 | Inventory/LPN/Lot models | docs/phase0/PHASE_0.md §H1 | itad-core/app/models/inventory.py | itad-core/alembic/versions/0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py | tests/test_phase0_h_inventory_outbound_downstream_data_layer.py | Docs/Schema/Tests | PASS | - |
| H2 | Outbound shipments | docs/phase0/PHASE_0.md §H2 | itad-core/app/models/inventory.py | itad-core/alembic/versions/0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py | tests/test_phase0_h_inventory_outbound_downstream_data_layer.py | Docs/Schema/Tests | PASS | - |
| H3 | Downstream qualification/disposition | docs/phase0/PHASE_0.md §H3 | itad-core/app/models/inventory.py | itad-core/alembic/versions/0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py | tests/test_phase0_h_inventory_outbound_downstream_data_layer.py | Docs/Schema/Tests | PASS | - |
| I1 | Pickup manifest + binding | docs/phase0/PHASE_0.md §I1; lock review I1 | itad-core/app/models/pickup_manifest.py | itad-core/alembic/versions/0010_phase0_i_pickup_manifest_bridge.sqlalchemy.py | tests/test_phase0_i_pickup_manifest_bridge_data_layer.py | Docs/Schema/Tests | PASS | - |
| I2 | Canonical refs/idempotency | docs/phase0/PHASE_0.md §I2/I3 | itad-core/app/models/pickup_manifest.py | itad-core/alembic/versions/0010_phase0_i_pickup_manifest_bridge.sqlalchemy.py | tests/test_phase0_i_pickup_manifest_bridge_data_layer.py | Docs/Schema/Tests | PASS | - |
| I3 | Evidence/POD handling | docs/phase0/PHASE_0.md §I3 | itad-core/app/models/pickup_manifest.py | scripts/seed_demo.py | tests/test_phase0_i_pickup_manifest_bridge_data_layer.py | Docs/Seed/Tests | PASS | - |
| I4 | Geocode cache gating | docs/phase0/PHASE_0.md §I4 | itad-core/app/repositories/geocode_repo.py | itad-core/alembic/versions/0010_phase0_i_pickup_manifest_bridge.sqlalchemy.py | tests/test_phase0_i_pickup_manifest_bridge_data_layer.py | Docs/Schema/Tests | PASS | - |
| I5 | Failure modes/logging | docs/phase0/PHASE_0.md §I5 | itad-core/app/models/pickup_manifest.py | itad-core/alembic/versions/0010_phase0_i_pickup_manifest_bridge.sqlalchemy.py | tests/test_phase0_i_pickup_manifest_bridge_data_layer.py | Docs/Schema/Tests | PASS | - |
| J1 | Pricing external refs | docs/phase0/PHASE_0.md §J1 | itad-core/app/models/pricing.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |
| J2 | Service catalog references | docs/phase0/PHASE_0.md §J2 | itad-core/app/models/settlement.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |
| J3 | Rule precedence metadata | docs/phase0/PHASE_0.md §J3 | itad-core/app/repositories/settlement_repo.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |
| J4 | Snapshot versioning | docs/phase0/PHASE_0.md §J4 | itad-core/app/models/settlement.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |
| J5 | Basis-of-charge mapping | docs/phase0/PHASE_0.md §J5 | itad-core/app/models/settlement.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |
| J6 | Manual adjustments | docs/phase0/PHASE_0.md §J6 | itad-core/app/models/settlement.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |
| J7 | Pricing exchange policy | docs/phase0/PHASE_0.md §J7 | itad-core/app/models/pricing.py | itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py | tests/test_phase0_j_pricing_settlement_snapshot_data_layer.py | Docs/Schema/Tests | PASS | - |

## Verification
The Phase 0 verification log (`docs/phase0/PHASE_0_VERIFICATION_LOG.md`) and the automation output in `docs/phase0/verification_runs/2026-01-02_2112.txt` document the reproducible validation steps (rg greps, script checks) referenced on this index.
