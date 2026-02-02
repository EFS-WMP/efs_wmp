# Manifest

## Changed/Created Files

- `addons/common/itad_core/models/itad_outbox.py`: Defaults for idempotency/correlation, deterministic payload hashing, and secure requeue without sudo bypass.
- `addons/common/itad_core/security/ir.model.access.csv`: Qualified receiving manager XMLID and ensured create access for base users.
- `addons/common/itad_core/tests/__init__.py`: _assertRaises patch now supports tuples while preserving UserError no-savepoint behavior.
- `addons/common/itad_core/tests/test_assert_raises_no_savepoint.py`: Regression tests for tuple/class handling of the custom assertRaises helper.
- `addons/common/itad_ci_tests/` (new addon): CI regression tests for outbox ACL create, backoff jitter determinism, and assertRaises helper behavior.
- `addons/common/itad_core/tests/test_material_sync_contract.py`: Aligns with real sync contract (warning + structured failure stats).
- `addons/common/itad_core/security/ir.model.access.csv`: Added create access for basic users and receiving managers on `itad.core.outbox`; manager write retained.
- `addons/common/itad_core/tests/test_fsm_itad_outbox_access_basic.py`: Ensures basic user can create outbox rows (ACL regression guard).
- `addons/common/itad_core/tests/test_fsm_itad_outbox_access_requeue.py`: Verifies requeue denied to non-managers and allowed for receiving managers.
- `addons/common/itad_core/tests/test_material_sync_contract.py`: Downgrades missing wrapper log path to warning and asserts graceful handling.
- `runbook_odoo_quality_checks.md`: Pointer to the canonical Odoo 18 quality gates runbook under `docs/`.
- `docs/runbook_odoo_quality_checks.md`: Runbook of install smoke tests, addons_path/OCA checks, manifest coverage, SoR guardrails, and cron/registry smoke checks for Odoo 18.
- `addons/common/itad_core/scripts/capture_phase2_2a_test_evidence.py`: Captures Phase 2.2a one-shot Odoo test output, DB list, sha256s, and summary metadata under `docs/evidence/phase2.2a/`.
- `addons/common/itad_core/tests/test_phase2_2a_evidence_docs.py`: Smoke-test asserting Phase 2.2a evidence paths and canonical commands are referenced in repo runbooks.
- `docker/odoo18/docker-compose.odoo18.yml`: Mounts repo root read-only at `/mnt/odoo-dev` for doc-verification tests.
- `addons/common/itad_core/tests/__init__.py`: In test mode, run `TransactionCase` UserError assertions without savepoint rollback so audit logs and wizard state persist for Phase 2.2 tests.
- `addons/common/itad_core/tests/_helpers.py`: Creates FSM fixtures in the active transaction with required `location_id` and ITAD fields for Phase 2.2 tests.
- `addons/common/itad_core/models/itad_receiving_wizard.py`: Keeps wizard state and audit log writes in the active transaction to align with Phase 2.2 test expectations.
- `scripts/odoo_ci_checks.py`: Adds offline Odoo addon hygiene checks (DISABLED files, missing manifests in addons paths, and manifest coverage with an allowlist).
- `scripts/odoo_ci_allowlist.txt`: Allowlist for CI hygiene checks (supports manifest coverage and missing-manifest exceptions).
- `itad-core/pyproject.toml`: Pinned the test extras so `httpx < 0.28` (and `httpcore < 0.17`) keeps `AsyncClient(app=...)` working in the container while retaining the optional test suite.
- `itad-core/tests/conftest.py`: Seeds a canonical `bol-123` anchor before each session so receiving tests can insert records without manual setup.
- `itad-core/tests/test_receiving.py`: Converts `occurred_at` to an ISO timestamp in the payload so Httpx can serialize it; the Pydantic model still parses a proper `datetime`.
- `itad-core/app/scripts/seed_demo.py`: Avoids the `discrepancy_blockers` name clash, reports the blockers list, and uses hex-valid SHA256 placeholders for the final-proof artifact.
- `itad-core/alembic/versions/0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py`: Restored numeric revision identifiers and fixed the `computed_lines_json` default to `'{"lines": []}'::jsonb` for stable migrations.
- `docs/phase0/PHASE_0_VERIFICATION_LOG.md`: Appended the 2026-01-03 05:56 UTC row summarizing the `alembic upgrade`, `pytest`, `seed_demo`, SoR guard, validator, and grep outputs that prove Step 6.
- `tasks.md`: Logs Phase 0 Step 6, ties the evidence index PASS to the verification run, and enumerates all commands that were executed to close the gate.
- `docs/phase0/PHASE_0_SIGNOFF_SUMMARY.md`: One-page closure pack stating the locked SoR policy, canonical object chain, integration boundaries, key guarantees, deferrals, and links to the sign-off artifacts.
- `docs/phase0/PHASE_0_RISK_REGISTER.md`: Top-10 risk register with impacts, likelihood, mitigations, and owners tied to SoR/compliance concerns.
- `docs/phase0/PHASE_1_READINESS_GATE.md`: Readiness checklist for gating Phase 1, including SoR guard verifications, evidence index PASS, pickup manifest contract lock, and readiness verification commands.
- `docs/phase0/PHASE_0_LOCK_REVIEW.md`: Sign-off Bundle section now references the new closure pack docs, readiness checklist, and verification log.
- `tasks.md`: Step 7 entry records the new closure pack artifacts, readiness gate commands, and the Phase 1 BLOCKED note until the gate passes.
- `itad-core/app/api/v1/pickup_manifests.py`: Enhanced SoR guard to recursively scan payload but EXEMPT snapshot fields (`*_snapshot_json`, `snapshot_json`) from validation.
- `itad-core/tests/test_sor_guard_snapshot_exemptions.py`: New test suite validating SoR guard snapshot exemption rules.

## Key Decisions

### Odoo 18 Quality Gates Runbook
Documented the installability smoke test, addons_path/OCA checks, manifest coverage via `scripts/odoo_ci_checks.py`, and post-install registry/cron validation in a single runbook for consistent pre-merge checks.

### Phase 2.2a Evidence Capture and CI Gate
Evidence capture is standardized via a one-shot compose run that writes audit artifacts under `docs/evidence/phase2.2a/`. CI gate integration is pending until an existing CI configuration is added to the repo.

### Phase 2.2 Test Stabilization
Phase 2.2 tests require UserError paths to persist audit logs and wizard state; test harness now avoids savepoint rollback for UserError assertions to keep those records visible within the same test transaction.

### Phase 1 SoR Guard Clarification
Operational-truth keys are forbidden EXCEPT inside snapshot fields. The SoR guard recursively scans but exempts keys matching `snapshot_json` or ending with `_snapshot_json`.

- Phase 0 is now formally closed with the closure pack (`PHASE_0_SIGNOFF_SUMMARY.md`, `PHASE_0_RISK_REGISTER.md`, `PHASE_1_READINESS_GATE.md`), and Phase 1 remains BLOCKED until the readiness gate confirms PASS with SoR guard plus evidence validation.
- Canonical Phase 0 docs keep the locked SoR wording, so rerunning the SoR guard and `rg -n "archive/" docs/phase0 -S` is required before Phase 1 planning resumes.
- Phase 0 evidence (A1–I30) still records PASS in `docs/phase0/PHASE_0_EVIDENCE_INDEX.md`, and the latest verification row in `docs/phase0/PHASE_0_VERIFICATION_LOG.md` proves the `alembic`, `pytest`, `seed_demo`, guard, validator, and grep commands executed prior to considering Phase 1.

## Tests & Verification

- `docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml run --rm -T odoo18 odoo --test-enable -d odoo18_db -c /etc/odoo/odoo.conf -u itad_core --stop-after-init --no-http`
- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core alembic upgrade head`
- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m pytest -q` (46 passed in 17.06s)
- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m app.scripts.seed_demo`
- `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1` (SoR guard passes)
- `python scripts/phase0_validate_evidence_index.py` (all referenced paths exist)
- `rg -n "\| (PARTIAL|FAIL) \|" docs/phase0/PHASE_0_EVIDENCE_INDEX.md` (no matches)
- `rg -n "archive/" docs/phase0 -S` (0 matches; canonical docs reference no archive paths)

## Odoo Audit Checklist & CI Gates (Phase 2.x)

### Close the Installability Blocker First
- Confirm `addons_path` inside the running container matches the mounted paths (see `docker/odoo18/odoo.conf` and `docker/odoo18/docker-compose.odoo18.yml`).
- Confirm dependencies are loadable in the same environment (`fieldservice` is required by `addons/common/itad_core/__manifest__.py`).
- Re-run `-u itad_core` after fixing discovery and dependency issues. Until this is resolved, any dead-code or manifest-coverage work is speculative.

### Dead Code Verification Checklist (Required Before Removal)
- Inspect `__manifest__.py` for `data`, `demo`, `assets`, and `qweb` coverage.
- Grep file names across the repo (including view inheritance references) before declaring files unused.
- Only then remove or archive unreferenced XML/templates.

### Demo Data Policy
- If `demo.xml` is retained but not loaded in production, explicitly document that policy.
- If demo data is loaded, wire it under `demo` (not `data`) and add a deployment guardrail.

### CI Gate Design (Avoid Over-Tightening)
- `scripts/odoo_ci_checks.py` enforces:
  - `.DISABLED` file presence (fail fast).
  - Missing `__manifest__.py` in addons paths (fail fast).
  - Manifest coverage for XML/CSV under standard directories, with allowlist support.
- Use `scripts/odoo_ci_allowlist.txt` to allow intentional scaffolding/templates.

### SoR Boundary Guardrail (Odoo Registry + Cron)
- After install/upgrade, confirm the outbox cron records and models are present in the registry.
  - Verify `ir.cron` records for `itad_core.ir_cron_itad_outbox_process` and `itad_core.cron_archive_receipt_audit_logs`.
  - Verify models are loaded: `itad.core.outbox`, `itad.core.config`, `itad.receipt.audit.log`.
