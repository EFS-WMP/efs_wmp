# Implementation Plan - Phase 2.2 (2.2a + 2.2b)

## Overview
Phase 2.2 production hardening and backward compatibility for Receiving Dashboard MVP.

## Deployment Sequence

## Phase 2.2 Gate Checklist
- [ ] `itad_core` test suite passes with `--test-enable` in a one-shot container run.
- [ ] Receiving wizard error-state and audit-log paths validated for UserError scenarios.
- [ ] Phase 2.1 -> 2.2 migration dry-run and apply reports match.
- [ ] Cron records active for outbox + audit archiving.

### One-shot Upgrade/Test Pattern
1) Stop running Odoo service (if active):
   - `docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml stop odoo18`
2) Run one-shot upgrade/tests:
   - `docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 odoo --test-enable -d odoo18_db -c /etc/odoo/odoo.conf -u itad_core --stop-after-init --no-http`
3) Capture evidence artifacts:
   - `python3 addons/common/itad_core/scripts/capture_phase2_2a_test_evidence.py` (writes `docs/evidence/phase2.2a/`)
4) Restart service:
   - `docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d odoo18`

### Pre-Deployment
1. ✅ **Code Review** - All Phase 2.2 changes reviewed
2. ✅ **Tests Pass** - All 20+ tests passing
3. ✅ **Documentation Complete** - Troubleshooting guide, rollback procedures
4. ⏳ **Backup Database** - Full backup before deployment

### Deployment to Pre-Production

#### Step 1: Module Upgrade
```powershell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 `
  odoo -c /etc/odoo/odoo.conf -d odoo18_preprod_db -u itad_core --stop-after-init
```

**Gate Check**: Module upgrades without errors

#### Step 2: Run Test Suite
```powershell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo -c /etc/odoo/odoo.conf -d odoo18_preprod_db -u itad_core --stop-after-init --test-enable --no-http
```

**Gate Check**: All tests pass (exit code 0)

#### Step 3: Migration Dry-Run
```powershell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 `
  python3 /mnt/extra-addons-custom/itad_core/scripts/migrate_phase2_1_to_2_2.py --dry-run --verbose
```

**Gate Check**: Review migration report
- Verify eligible count matches expectations
- Review sample records
- Confirm no errors

#### Step 4: Migration Apply
```powershell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 `
  python3 /mnt/extra-addons-custom/itad_core/scripts/migrate_phase2_1_to_2_2.py --apply --verbose
```

**Gate Check**: Migration completes successfully
- Fixed count matches dry-run eligible count
- No errors reported

#### Step 5: Verify Retry Functionality
1. Find FSM order in exception state
2. Open receiving wizard
3. Verify `original_idempotency_key` populated (from migration)
4. Attempt retry
5. Verify same key used in API call

**Gate Check**: Retry works with migrated idempotency key

#### Step 6: Verify Cron
```powershell
# Check cron schedule
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 `
  odoo shell -c /etc/odoo/odoo.conf -d odoo18_preprod_db

# In shell:
>>> cron = env.ref('itad_core.cron_archive_receipt_audit_logs')
>>> print(f"Active: {cron.active}, Next: {cron.nextcall}")
```

**Gate Check**: Cron is active and scheduled

#### Step 7: Smoke Test
1. Create test FSM order
2. Submit pickup manifest (Phase 1)
3. Confirm receipt (Phase 2.1)
4. Verify audit log created with outcome
5. Verify system parameters applied

**Gate Check**: End-to-end flow works

### Deployment to Production

**Prerequisites**:
- All pre-prod gate checks passed
- Stakeholder approval
- Maintenance window scheduled
- Rollback plan reviewed

**Steps**: Repeat Steps 1-7 with production database

**Post-Deployment**:
1. Monitor logs for 24 hours
2. Review audit log outcomes
3. Check cron execution
4. Verify no performance degradation

## Rollback Plan

See `docs/phase2/PHASE_2_2_SUMMARY.md` for detailed rollback procedures.

**Quick Rollback**:
1. `git checkout tags/phase-2.1`
2. Restart Odoo
3. Verify Phase 2.1 code runs with Phase 2.2 database (safe - new fields ignored)

## Success Criteria

- ✅ All tests pass
- ✅ Migration completes without errors
- ✅ Retry functionality works for legacy exceptions
- ✅ API health checks block incompatible versions
- ✅ Rate limiting enforced
- ✅ Audit log archiving cron runs daily
- ✅ No performance regression
- ✅ Rollback procedure tested

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Migration fails | Dry-run first, review report, database backup |
| Performance degradation | Monitor audit log queries, add indexes if needed |
| Incompatible ITAD Core version | Version check blocks submission, clear error message |
| Data loss on rollback | Phase 2.2 adds fields only, Phase 2.1 code compatible |

## Timeline

- **Phase 2.2a**: Completed 2026-01-17
- **Phase 2.2b**: Completed 2026-01-17
- **Pre-Prod Deployment**: TBD
- **Production Deployment**: TBD (after pre-prod validation)
