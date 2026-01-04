# Codex Execution Checklist (Definition of Done)

Purpose: This checklist must be completed for every Codex change set / PR.

## A) Universal DoD (All Phases)
- [ ] Scope guard: confirm we are not skipping Phase 0; Phase 1 is blocked until Phase 0 Lock Review is complete.
- [ ] SoR wording check: "Acceptance/dispatch commits to Odoo; ITAD Core receives compliance artifacts later via pickup_manifest -> BOL -> receiving..."
- [ ] Update docs if impacted (docs/phase0/PHASE_0.md, docs/phase0/PHASE_0_LOCK_REVIEW.md, docs/phase0/glossary.md, docs/phase0/object_map.md).
- [ ] DB changes: Alembic migration added and reversible (if schema changed).
- [ ] Tests: add/update tests and run pytest -q (container or host).
- [ ] Seed/demo: update app/scripts/seed_demo.py if the feature affects demo flows.
- [ ] Tracking: ALWAYS update repo-root manifest.md + implementation_plan.md.
- [ ] Tracker: update repo-root tasks.md (Phase 0 master checklist) when Phase 0 items are affected.
- [ ] Consistency: search repo for contradictory statements (e.g., "acceptance commits to ITAD Core") and fix.

## B) Phase 0-Specific DoD (Extras)
- [ ] Phase 0 checklist item(s) updated in docs/phase0/PHASE_0_LOCK_REVIEW.md.
- [ ] Evidence pointers added to tasks.md (doc paths + migration + tests).
- [ ] Phase 1 remains marked BLOCKED in implementation_plan.md until Phase 0 is fully checked.

## C) Command Snippets
```bash
docker compose -f docker-compose.itad-core.yml exec itad-core pytest -q
alembic upgrade head
rg -n "Acceptance/dispatch commits to Odoo" -S .
```
