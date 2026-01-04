# Phase 1 Readiness Gate

| Check | How to Verify | Pass Criteria |
| --- | --- | --- |
| 1. SoR Guardrails intact | `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1` | Script exits code 0 and prints PASS. |
| 2. Evidence Index all PASS | `rg -n "\| (PARTIAL|FAIL) \|" docs/phase0/PHASE_0_EVIDENCE_INDEX.md` | No matches; table shows PASS for A1–I30. |
| 3. Verification log documents latest run | `docs/phase0/PHASE_0_VERIFICATION_LOG.md` | Latest row (e.g., 2026-01-03 05:56 UTC) references alembic/test/seed/guard/validator commands. |
| 4. Phase 0 lock review complete | `docs/phase0/PHASE_0_LOCK_REVIEW.md` | All checkboxes A–I marked [x] and “Sign-off Bundle” references added. |
| 5. Pickup manifest bridge contract locked | Review `docs/phase0/PHASE_0.md` section I + `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` I30. | Contract states 1 manifest → 1 BOL, state machine, idempotency, geocode gating, correlation logging. |
| 6. Idempotency header contract verified | Inspect receiving & pickup endpoints (`itad-core/app/api/v1/receiving.py`, `bol.py`). | POST handlers require `Idempotency-Key` header; tests use header. |
| 7. Blind receiving behavior locked | `docs/phase0/PHASE_0.md` D + `tests/test_receiving.py` | Declared weights hidden in blind mode until admin header toggles include. |
| 8. Taxonomy + processing sessions locked | `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` E17-E20 | Session/line tables, taxonomy_item FK, sb20 flag, no free-text. |
| 9. Reconciliation/dispute gating enforced | Inspect `itad-core/app/repositories/reconciliation_repo.py` + `docs/phase0/PHASE_0.md` F | Over-threshold runs block closure until approval; open discrepancies block. |
| 10. Evidence & custody append-only | `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` G24-G26 | `evidence_artifact`, `artifact_link`, `custody_event` tables exist and repos enforce visibility. |
| 11. Inventory/outbound/downstream anchored | `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` H27-H29 | Location/LPN/lot/shipment/disposition tables + custody updates validated in seed. |
| 12. Pricing snapshot placeholders locked | `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` J31 | `settlement_pricing_snapshot` and `pricing_external_ref` capture hashes; adjustments require approver. |
| 13. Verification scripts checked into repo | `scripts/phase0_verify.ps1`, `scripts/phase0_validate_evidence_index.py` | Scripts present; `phase0_verify` documents command list and stores logs. |
| 14. Routific caller decision locked | `tasks.md` Phase 1 Pre-Start Gate + `docs/phase0/PHASE_0.md` integration section | Explicit statement: "Routific is called from Odoo; ITAD Core stores trace-only `routific_job_id/input_hash`." |
| 15. Phase 1 unblock condition met | `docs/phase0/PHASE_1_READINESS_GATE.md` review | All above checks PASS and Phase 0 sign-off docs signed; log time & reviewer in sign-off summary. |
