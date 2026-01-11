# Manifest

## Changed/Created Files

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

### Phase 1 SoR Guard Clarification
Operational-truth keys are forbidden EXCEPT inside snapshot fields. The SoR guard recursively scans but exempts keys matching `snapshot_json` or ending with `_snapshot_json`.

- Phase 0 is now formally closed with the closure pack (`PHASE_0_SIGNOFF_SUMMARY.md`, `PHASE_0_RISK_REGISTER.md`, `PHASE_1_READINESS_GATE.md`), and Phase 1 remains BLOCKED until the readiness gate confirms PASS with SoR guard plus evidence validation.
- Canonical Phase 0 docs keep the locked SoR wording, so rerunning the SoR guard and `rg -n "archive/" docs/phase0 -S` is required before Phase 1 planning resumes.
- Phase 0 evidence (A1–I30) still records PASS in `docs/phase0/PHASE_0_EVIDENCE_INDEX.md`, and the latest verification row in `docs/phase0/PHASE_0_VERIFICATION_LOG.md` proves the `alembic`, `pytest`, `seed_demo`, guard, validator, and grep commands executed prior to considering Phase 1.

## Tests & Verification

- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core alembic upgrade head`
- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m pytest -q` (46 passed in 17.06s)
- `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m app.scripts.seed_demo`
- `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1` (SoR guard passes)
- `python scripts/phase0_validate_evidence_index.py` (all referenced paths exist)
- `rg -n "\| (PARTIAL|FAIL) \|" docs/phase0/PHASE_0_EVIDENCE_INDEX.md` (no matches)
- `rg -n "archive/" docs/phase0 -S` (0 matches; canonical docs reference no archive paths)
