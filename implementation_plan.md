# Implementation Plan

## Current Status
- **Phase 0: Canonical Model Lock** - Complete (pending formal sign-off)
  - Phase 0.A: Architecture & Ownership - Complete
  - Phase 0.B: Identifiers & Versioning - Complete
  - Phase 0.C: Workflow (Gates, Stages, Closure) - Complete
  - Phase 0.D: Receiving Anchor (Immutable) - Complete
  - Phase 0.E: Processing Domains & Taxonomy - Complete
  - Phase 0.F: Reconciliation & Disputes (data layer) - Complete
  - Phase 0.G: Evidence & Chain of Custody (data layer) - Complete
  - Phase 0.H: Inventory, Outbound, Downstream (data layer) - Complete
  - Phase 0.I: Variant A Integrations (Pickup Manifest bridge) - Complete
  - Phase 0.J: Commercials & Pricing Addendum (policy lock + settlement snapshots) - Complete
  - Phase 0 Step 7: Closure Pack & Readiness Gate - Complete
  - Phase 0 Step 6: Evidence Index PASS + verification run recorded - Complete
- **Maintenance:** Idempotency contract enforced; geocode cache gates in place; pricing snapshot/adjustment data layer added; test suite passing in container (`docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core pytest -q`).

## Roadmap Alignment
- Canonical roadmap: docs/ROADMAP.md
- Phase 1 is BLOCKED until Phase 0 checklist items (tasks.md) are signed off.
- Codex DoD checklist required for every change set: CODEX_CHECKLIST.md

### Phase 0 Step 1: Doc Canonicalization (Complete)
- **Objective:** Deduplicate Phase 0 docs, archive drafts, and reinforce the Odoo/ITAD Core SoR lock before Phase 1.
- **Verification:** `rg -n "system of record for all operational data" docs/phase0` (0 matches); `rg -n "ITAD Core serves as the system of record" docs/phase0` (canonical summary only); `rg -n "acceptance.*commits to ITAD Core" docs/phase0` (0 matches); `rg -n "PHASE_0\.md|PHASE_0_LOCK_REVIEW\.md|glossary\.md|object_map\.md" -S docs/phase0` (canonical files only). All duplicated tasks docs moved to `docs/phase0/archive/2026-01-02/`.

### Phase 0 Step 2: Evidence Index (Complete)
- **Objective:** Provide a verifiable index linking each Phase 0 checklist item to docs/schemas/tests.
- **Verification:** `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` reviewed; `python scripts/phase0_validate_evidence_index.py` validates referenced paths.

### Phase 0 Step 3: Verification Log (Complete)
- **Objective:** Record a reproducible command suite that validates Phase 0 evidence integrity.
- **Verification:** `scripts/phase0_verify.ps1` executed; log saved at `docs/phase0/verification_runs/2026-01-02_2112.txt`; the latest 2026-01-03 05:56 UTC row in `docs/phase0/PHASE_0_VERIFICATION_LOG.md` documents the `alembic upgrade`, `pytest`, `seed_demo`, SoR guard, validator, and grep outputs that cover the canonical checks.

### Phase 0 Step 6: Evidence Index PASS + verification run recorded (Complete)
- **Objective:** Confirm every Phase 0 checklist item now lists PASS evidence and record the final verification run that exercises migrations/tests/seed/guard/validator/grep commands.
- **Verification:** `docs/phase0/PHASE_0_EVIDENCE_INDEX.md` shows PASS statuses for A1–I30; `docs/phase0/PHASE_0_VERIFICATION_LOG.md` now contains the 2026-01-03 05:56 UTC row with the list of commands.
- **Commands executed:**
  1. `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core alembic upgrade head`
  2. `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m pytest -q`
  3. `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec itad-core python -m app.scripts.seed_demo`
  4. `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1`
  5. `python scripts/phase0_validate_evidence_index.py`
  6. `rg -n "\| (PARTIAL|FAIL) \|" docs/phase0/PHASE_0_EVIDENCE_INDEX.md`

### Phase 0 Step 7: Closure Pack & Readiness Gate (Complete)
- **Objective:** Bundle the closure artifacts, codify the Phase 1 readiness gate, and ensure canonical docs reference no archived content while SoR guard runs before unlocking Phase 1.
- **Verification:** `docs/phase0/PHASE_0_SIGNOFF_SUMMARY.md`, `docs/phase0/PHASE_0_RISK_REGISTER.md`, and `docs/phase0/PHASE_1_READINESS_GATE.md` exist; `docs/phase0/PHASE_0_LOCK_REVIEW.md` links to them in the Sign-off Bundle; canonical docs contain the locked SoR statement; `docs/phase0/PHASE_0_VERIFICATION_LOG.md` records runs for the SoR guard and `rg -n "archive/" docs/phase0 -S`.
- **Commands executed:**
  1. `rg -n "archive/" docs/phase0 -S`
  2. `powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1`
  3. Confirm `docs/phase0/PHASE_0_SIGNOFF_SUMMARY.md`, `docs/phase0/PHASE_0_RISK_REGISTER.md`, and `docs/phase0/PHASE_1_READINESS_GATE.md` exist and are referenced from the lock review.

### Phase 0 Step 4: Tracker normalization (Complete)
- **Objective:** Ensure only `tasks.md` and `docs/phase0/PHASE_0_LOCK_REVIEW.md` remain active trackers and that all docs reference them.
- **Verification:** `rg -n "tasks\.md|PHASE_0_LOCK_REVIEW\.md" README.md docs/ROADMAP.md docs -S` confirms canonical references; duplicates archived under `docs/phase0/archive/2026-01-02/`.

## Next Steps (Phases/Sprints)

### Phase 0 Sign-off & Handoff
- **Priority:** P0
- **Status:** Pending sign-off
- **Tasks:** Circulate tasks.md and docs/phase0 updates for approval; confirm `PHASE_0_SIGNOFF_SUMMARY.md`, `PHASE_0_RISK_REGISTER.md`, and `PHASE_1_READINESS_GATE.md` exist and are referenced from the sign-off bundle; rerun the SoR guard plus `rg -n "archive/" docs/phase0 -S` and the evidence-index validator; capture the results in `docs/phase0/PHASE_0_VERIFICATION_LOG.md`; reassert the Routific caller decision (Odoo) before Phase 1 starts.
- **Acceptance Criteria:** tasks.md shows 31/31 checked with evidence and Step 7 documented; PHASE_0_LOCK_REVIEW.md references the closure pack; manifest.md/implementation_plan.md describe the readiness gate; Phase 1 remains BLOCKED until the readiness gate passes and the closure pack is approved.

### Phase 1: Core Integration (BLOCKED until Phase 0 sign-off)

#### Phase 1 Unblocker (MUST pass before Phase 1 gates)
**Objective:** Make Odoo discover + load `itad_core` so Phase 1 Odoo tests and UI fields/actions exist.

**Evidence from sanity check (current blockers):**
- itad_core not installable / module not found; module path False.
- `addons_path` includes `/mnt/extra-addons-custom/itad_core` (likely module folder vs addons root).
- prior test run failed to start due to port 8069 already in use.

**Unblocker Tasks (explicit)**
1) Fix addons_path/mount layout so addons_path points to an addons root (e.g. `/mnt/extra-addons-custom`), not the module folder.
2) Verify `__manifest__.py` has `installable: True` and valid `depends`.
3) Verify discovery:
   - `mm.get_module_path('itad_core') != False`
   - no “not installable, skipped”
   - registry contains `itad.core.outbox` and fsm.order fields + action exist

**Unblocker Gate Commands**
- Discovery:
  - `docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 sh -lc "ls -la /mnt/extra-addons-custom && ls -la /mnt/extra-addons-custom/itad_core/__manifest__.py"`
  - `docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 sh -lc "python3 - <<'PY'
import ast, pathlib
p = pathlib.Path('/mnt/extra-addons-custom/itad_core/__manifest__.py')
d = ast.literal_eval(p.read_text(encoding='utf-8'))
print('installable:', d.get('installable'))
print('depends:', d.get('depends'))
PY"`
  - `docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 sh -lc "printf '%s\n' \"import odoo.modules.module as mm\" \"print(mm.get_module_path('itad_core'))\" | odoo shell -c /etc/odoo/odoo.conf -d odoo18_fs"`

#### Robust Gate Commands (canonical paths; avoids port conflicts)
- ITAD Core:
  - `docker compose -f C:\odoo_dev\itad-core\docker-compose.itad-core.yml exec -T itad-core pytest -q`
- Odoo (one-off container; avoids 8069 collisions):
  - `docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml run --rm odoo18 odoo -c /etc/odoo/odoo.conf -d odoo18_fs -u itad_core --test-enable --stop-after-init --no-http`

**Tests:** UNVERIFIED until Unblocker passes and gate command outputs are attached.

**Repo cleanliness (must pass before recording evidence):**
- `git status` must be clean (or changes committed as doc/evidence update).


### Phase 2: Advanced Features
- **Priority:** Medium
- **Tasks:** Evidence handling enhancements, inventory/downstream workflows, reporting, RBAC.
- **Acceptance Criteria:** Full processing workflow with audit trails and role enforcement.

### Phase 3: Scaling and Compliance
- **Priority:** Low
- **Tasks:** Multi-tenant readiness, performance tuning, security/compliance hardening.
- **Acceptance Criteria:** Production-ready with audit readiness and reporting SLAs met.
