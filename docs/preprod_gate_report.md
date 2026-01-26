# Phase 2.2 Pre-Prod Gate Rehearsal Report — itad_core

> Scope: deployment validation + evidence collection only (no business feature changes).

## Summary
- **Date/Time (UTC):** 2026-01-26T07:41:22Z
- **Environment:** Pre-Prod (Odoo 18)
- **Operator:** _TBD_
- **Outcome:** FAILED (Docker runtime unavailable in environment)
- **Phase:** Phase 2.2 Hardening / Go-No-Go Gate

## Preconditions
- ✅ Backup captured and verified restore path
- ✅ Rollback plan reviewed
- ✅ SoR boundaries acknowledged (Odoo not SoR for compliance artifacts)

## Commands & Results
> Use the same addons paths as CI and the canonical Odoo 18 docker compose file.

### 1) Install Smoke (-i itad_core)
```bash
# Install smoke
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 \
  odoo -c /etc/odoo/odoo.conf -d <PREPROD_DB> -i itad_core --stop-after-init
```
- **Result:** FAILED (docker not available)
- **Evidence:** `docs/evidence/phase2.2/logs/preprod_gate_rehearsal_2026-01-26T074122Z.log`

### 2) Upgrade Smoke (-u itad_core)
```bash
# Upgrade smoke
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 \
  odoo -c /etc/odoo/odoo.conf -d <PREPROD_DB> -u itad_core --stop-after-init
```
- **Result:** BLOCKED (docker not available)
- **Evidence:** `docs/evidence/phase2.2/logs/preprod_gate_rehearsal_2026-01-26T074122Z.log`

### 3) Registry + Cron Validation
```bash
# Odoo shell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 \
  odoo shell -c /etc/odoo/odoo.conf -d <PREPROD_DB>

# In shell (example)
# >>> env['ir.model'].search([('model', 'in', [
# ... 'itad.core.outbox',
# ... 'itad.core.config',
# ... 'itad.receipt.audit.log',
# ... ])])
# >>> env.ref('itad_core.cron_itad_core_outbox').active
# >>> env.ref('itad_core.cron_archive_receipt_audit_logs').active
```
- **Models validated:** BLOCKED (docker not available)
- **Crons validated:** BLOCKED (docker not available)
- **Evidence:** `docs/evidence/phase2.2/logs/preprod_gate_rehearsal_2026-01-26T074122Z.log`

### 4) E2E Smoke (Manifest → Receiving → Audit/Outbox)
> Minimal workflow that respects SoR boundaries and avoids mutating compliance truth in Odoo.

Checklist:
- [ ] Create pickup manifest (Phase 1 flow)
- [ ] Open receiving wizard and complete minimal receiving
- [ ] Verify audit log created
- [ ] Verify outbox record created and transitions through expected state(s)

- **Result:** BLOCKED (docker not available)
- **Evidence:** `docs/evidence/phase2.2/logs/preprod_gate_rehearsal_2026-01-26T074122Z.log`

## Artifact Capture
- **Console logs:** `docs/evidence/phase2.2/logs/` (store install/upgrade/test outputs)
- **Screenshots:** `docs/evidence/phase2.2/screenshots/` (cron list + outbox UI)
- **Checklist completion report:** _This document_ (filled)

## Backup / Rollback / Restore Validation
- **Backup created:** BLOCKED (docker not available)
- **Restore verified:** BLOCKED (docker not available)
- **Rollback rehearsal:** BLOCKED (docker not available)
- **Notes:** _TBD_

## Follow-up Tickets
> Create a ticket if any gate fails. Include exact error + reproduction steps.

- **Ticket ID:** PREPROD-GATE-DOCKER-MISSING
- **Summary:** Pre-prod gate rehearsal blocked: docker not available in execution environment
- **Repro Steps:** Run `docker version` in the execution environment; command fails with `bash: command not found: docker`.
- **Logs/Artifacts:** `docs/evidence/phase2.2/logs/preprod_gate_rehearsal_2026-01-26T074122Z.log`
