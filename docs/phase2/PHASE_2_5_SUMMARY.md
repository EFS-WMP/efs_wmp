# Phase 2.5 Summary: Ops Monitoring & Data Quality

## Overview

Phase 2.5 provides an Operations Health UI in Odoo for receiving managers to monitor sync status, outbox health, receipt exceptions, and data quality variances.

> [!IMPORTANT]
> SoR boundaries unchanged: ITAD Core = compliance SoR, Odoo = ops SoR + read cache.

---

## Components Delivered

### Operations Health Menu

**ITAD Core → Operations Health**
- Health Dashboard (kanban cards)
- Receiving Queues (Pending / Exceptions / Variance)
- Sync Status
- Outbox Health

### 3 Alert Conditions

| Code | Trigger | Severity |
|------|---------|----------|
| `TAXONOMY_STALE` | Stale > max_stale_hours | warn/critical |
| `OUTBOX_FAILURES` | Failed count > threshold | warn/critical |
| `RETENTION_DELETE_ENABLED` | retention_mode=delete | critical |

### Variance Detection

- Weight exceeds max threshold → flagged
- Review queue for managers
- Resolve action with notes

---

## Data Models

| Model | Purpose |
|-------|---------|
| `itad.ops.alert` | NEW - Alert cards for dashboard |
| `itad.taxonomy.sync.state` | +sync_state, stale_age computed |
| `fsm.order` | +6 variance fields |

---

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `variance.percent_threshold` | 25 | % delta for variance flag |
| `variance.absolute_lbs_threshold` | 500 | Lbs delta for variance flag |
| `ops.outbox_failures_threshold` | 5 | Failures before alert |
| `ops.outbox_window_minutes` | 60 | Window for counting failures |

---

## Scheduled Jobs

| Cron | Interval | Description |
|------|----------|-------------|
| `cron_itad_ops_alerts_compute` | 15 min | Recompute all alerts |
| `cron_itad_variance_evaluate` | 30 min | Flag variance on recent orders |

---

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `models/itad_ops_alert.py` | Alert model + compute_alerts() |
| `views/itad_ops_health_views.xml` | Dashboard, queues, forms |
| `views/itad_ops_menu.xml` | Menu structure |
| `data/itad_ops_cron.xml` | Cron jobs |
| `tests/test_ops_alerts.py` | Alert tests |
| `tests/test_variance.py` | Variance tests |

### Modified Files

| File | Change |
|------|--------|
| `models/fsm_order.py` | +6 variance fields + cron |
| `models/itad_taxonomy_sync_state.py` | +computed sync_state/stale_age |
| `security/ir.model.access.csv` | +ACL for itad.ops.alert |
| `data/itad_core_system_parameters.xml` | +variance/outbox params |
| `__manifest__.py` | Added new files |

---

## Test Commands

```powershell
cd c:\odoo_dev
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http
```

---

## Verification Checklist

- [ ] Operations Health menu visible to receiving managers
- [ ] Health Dashboard shows 3 alert cards
- [ ] Sync Status shows stale age and Sync Now button
- [ ] Outbox Health shows failed count with Retry
- [ ] Variance queue shows pending items with Resolve
- [ ] Tests pass: alert conditions + variance workflow
