# Operations Health Runbook

Daily monitoring guide for receiving managers.

---

## Daily Checklist

### 1. Check Health Dashboard

**Path**: ITAD Core → Operations Health → Health Dashboard

| Card | Action if Not OK |
|------|------------------|
| TAXONOMY_STALE | Click "Sync Now" or check API connectivity |
| OUTBOX_FAILURES | Open outbox, review errors, click "Retry Failed" |
| RETENTION_DELETE | If critical, check if intentional break-glass |

---

### 2. Review Exception Queue

**Path**: Operations Health → Receiving Queues → Receipt Exceptions

- Investigate each exception reason
- Open audit log for details
- Re-attempt receiving wizard if resolved

---

### 3. Process Variance Queue

**Path**: Operations Health → Receiving Queues → Variance Review

For each pending variance:
1. Review reason (weight delta, max exceeded)
2. Verify with physical inventory if needed
3. Click "Resolve" and add notes

---

## Alert Response Guide

### TAXONOMY_STALE (Warning/Critical)

**Cause**: Taxonomy sync hasn't run successfully

**Actions**:
1. Open Sync Status
2. Check last_error for API issues
3. Click "Sync Now" to attempt immediate sync
4. If persistent, check ITAD Core API health

---

### OUTBOX_FAILURES (Warning/Critical)

**Cause**: Multiple outbox records failing to send

**Actions**:
1. Open Outbox Health
2. Filter by "Failed"
3. Review last_error for each
4. Click "Retry" after fixing root cause
5. Common causes: API timeout, auth issues

---

### RETENTION_DELETE_ENABLED (Critical)

**Cause**: Audit log deletion is enabled (break-glass)

**Actions**:
1. Verify this is intentional (admin approval)
2. If not intentional, set `audit_retention_mode=archive`
3. If intentional, document reason and timeline
4. Disable after maintenance: set `delete_enabled=false`

---

## Configuration Reference

| Setting | Location | Default |
|---------|----------|---------|
| Max stale hours | System Parameters | 24 |
| Outbox failure threshold | System Parameters | 5 |
| Variance % threshold | System Parameters | 25 |
| Variance lbs threshold | System Parameters | 500 |

---

## Emergency Contacts

| Issue | Contact |
|-------|---------|
| API connectivity | IT Ops |
| Data quality questions | Operations Manager |
| Config changes | Admin/IT |
