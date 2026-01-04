# Phase 0 Closure Pack — Sign-off Summary

## Purpose
- Capture the locked decisions, guarantees, and sign-off pointers that prove Phase 0 is ready for review.

## Locked SoR Policy
- **Odoo = SoR for Scheduling / Routes / Dispatch execution.**
- **ITAD Core (FastAPI) = SoR for Compliance / Receiving / Processing / Custody / Evidence / Inventory / Settlement.**
- **Routific = optimizer-only; proposals stored/versioned in Odoo; ITAD Core receives compliance artifacts later via pickup_manifest → BOL → receiving.**

## Locked Canonical Object Chain
- Pickup Plan → Occurrence → Day Route → Pickup Manifest → BOL → Receiving → Processing Sessions → Lots/LPN → Shipments → Disposition → Settlement (see `docs/phase0/object_map.md`).

## Locked Glossary Scope
- BOL, Receiving Anchor, Workstream, Lot, LPN, Disposition, Settlement, Pickup Manifest, Evidence Artifact, Taxonomy Item, Stainless SoR guard terms (`docs/phase0/glossary.md`).

## Integration Boundaries
- Odoo dispatches/accepts routes and owns Routific invocation; ITAD Core ingests pickup_manifest payloads, records immutable compliance artifacts, and surfaces reconciliation/dispute state; Routific remains optimizer-only with cached `routific_job_id/input_hash` only for traceability (`tasks.md` gate, `docs/phase0/object_map.md`).

## Phase 0 Guarantees
- Immutable receiving records with void/reissue hooks; DB constraints enforce mandatory fields/tare policy and blind receiving redaction (`docs/phase0/PHASE_0.md` section D; `itad-core/app/schemas/receiving.py`; `docs/phase0/PHASE_0_EVIDENCE_INDEX.md: D13-D16`).
- Taxonomy-driven processing sessions (battery + ewaste) with hard rule `taxonomy_item_id`, SB20 flags, effective dating, append-only change log (`docs/phase0/PHASE_0.md` section E; `docs/phase0/PHASE_0_EVIDENCE_INDEX.md: E17-E20`).
- Reconciliation/dispute state machines that block closure when thresholds or discrepancies exist, with append-only approval/discrepancy tables (`docs/phase0/PHASE_0.md` section F; evidence index F21-F23).
- Evidence artifacts & custody events maintain immutable hashes/linkage, inventory/outbound/downstream models record locations/LPNs/vendors, pricing snapshots record settlement proofs, and pickup_manifest bridge locks Odoo refs to BOL (`docs/phase0/PHASE_0_EVIDENCE_INDEX.md` sections G31 and I30; `docs/phase0/SOR_LOCK.md` ensures SoR alignment).

## Known Deferrals (Phase 1+)
- Pickup manifest submission consumer/integration endpoints (Phase 1 API wiring).  
- Odoo Orch. for Routific acceptance and actual dispatch usage of `routific_job_id` (Phase 1).  
- RBAC/enrichment of compliance dashboards, advanced reconciliation tooling, and multi-site scaling (Phase 2+).  
- Pricing engine/enrichment beyond snapshot ingestion (Phase 2+).  

## Sign-off Checklist Pointers
- `docs/phase0/PHASE_0_LOCK_REVIEW.md` (final checklist)  
- `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` (proof A1–I30)  
- `docs/phase0/PHASE_0_VERIFICATION_LOG.md` (2026-01-03 05:56 UTC run)  
- `docs/phase0/PHASE_0_RISK_REGISTER.md` (top risks)  
- `docs/phase0/PHASE_1_READINESS_GATE.md` (Phase 1 unlock criteria)
