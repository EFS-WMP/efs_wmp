# Troubleshooting Guide - Receiving Dashboard

## Overview
This guide provides step-by-step troubleshooting for common receiving dashboard issues in Phase 2.2.

---

## API Connection Failed (API_UNREACHABLE)

### Symptoms
- Error message: "ITAD Core API is unreachable"
- Receipt confirmation fails immediately
- Audit log shows outcome: `API_UNREACHABLE`

### Diagnosis
1. **Check Audit Log**:
   - Navigate to: Technical → Database Structure → Models → `itad.receipt.audit.log`
   - Filter by: `outcome = API_UNREACHABLE`
   - Review `attempted_at` timestamp and `error_message`

2. **Verify Network Connectivity**:
   ```powershell
   # From Odoo container
   docker compose -p odoo18 -f docker\odoo18\docker-compose.odoo18.yml exec odoo18 sh
   curl -v http://itad-core:8001/health
   ```

3. **Check System Parameters**:
   - Settings → Technical → Parameters → System Parameters
   - Verify `itad_core.receipt_timeout_seconds` (default: 30)
   - Check ITAD Core base URL in `itad.core.config`

### Resolution
1. **ITAD Core Service Down**:
   - Start ITAD Core service
   - Verify health endpoint returns 200 OK

2. **Network Configuration**:
   - Check Docker network connectivity
   - Verify firewall rules
   - Confirm DNS resolution

3. **Timeout Too Low**:
   - Increase `itad_core.receipt_timeout_seconds` to 60
   - Retry receipt confirmation

---

## API Version Unsupported (API_VERSION_UNSUPPORTED)

### Symptoms
- Error message: "ITAD Core API version X.X.X is not supported"
- Audit log shows outcome: `API_VERSION_UNSUPPORTED`

### Diagnosis
1. **Check ITAD Core Version**:
   ```bash
   curl http://itad-core:8001/openapi.json | grep version
   ```

2. **Review Audit Log**:
   - Filter by: `outcome = API_VERSION_UNSUPPORTED`
   - Check `error_message` for detected version

### Resolution
1. **Upgrade ITAD Core**:
   - Minimum required version: 1.0.0
   - Follow ITAD Core upgrade procedure
   - Verify `/openapi.json` returns version >= 1.0.0

2. **Temporary Workaround** (if upgrade not immediately possible):
   - Contact system administrator
   - May require code patch to accept older version (NOT RECOMMENDED)

---

## Idempotency Key Conflict / Duplicate Return (DUPLICATE_RETURNED)

### Symptoms
- Receipt appears to succeed but returns existing record
- Audit log shows outcome: `DUPLICATE_RETURNED`
- ITAD Core returns 200 OK with previously created record

### Diagnosis
1. **Check Idempotency Key**:
   - View wizard audit information
   - Note `original_idempotency_key` value

2. **Search ITAD Core Logs**:
   ```sql
   SELECT * FROM receiving_weight_records 
   WHERE idempotency_key = 'receipt-XXXXX';
   ```

3. **Review Audit Log**:
   - Check all attempts for this order
   - Verify if previous attempt succeeded

### Resolution
1. **Legitimate Duplicate** (retry after success):
   - This is expected behavior
   - Idempotency prevents duplicate records
   - Verify FSM order state is "received"
   - No action needed

2. **Key Collision** (rare):
   - Review migration script execution
   - Check for manual key assignment errors
   - Contact system administrator

---

## Rate Limit Blocked (RATE_LIMIT_BLOCK)

### Symptoms
- Error message: "Rate limit exceeded. Maximum N attempts per hour"
- Audit log shows outcome: `RATE_LIMIT_BLOCK`
- User cannot retry receipt confirmation

### Diagnosis
1. **Check Recent Attempts**:
   - Audit log filter: `user_id = current user`, `order_id = current order`
   - Filter: `attempted_at >= (now - 1 hour)`
   - Count attempts

2. **Check Rate Limit Setting**:
   - System parameter: `itad_core.max_receipt_attempts_per_hour`
   - Default: 10 attempts

### Resolution
1. **Wait for Window to Reset**:
   - Rate limit window: 1 hour rolling
   - Oldest attempt will age out after 1 hour
   - Retry after window resets

2. **Increase Rate Limit** (if legitimate use case):
   - Settings → Technical → Parameters → System Parameters
   - Update `itad_core.max_receipt_attempts_per_hour` to higher value (e.g., 20)
   - Requires receiving manager permissions

3. **Investigate Root Cause**:
   - Why are so many attempts needed?
   - Check for validation errors
   - Review API connectivity issues

---

## Validation Error (VALIDATION_ERROR)

### Symptoms
- Error message shows specific validation failure
- Common: "BOL format invalid", "Weight must be greater than zero"
- Audit log shows outcome: `VALIDATION_ERROR`

### Diagnosis
1. **Review Error Message**:
   - Wizard displays specific validation error
   - Check audit log `error_message` field

2. **Common Validation Rules**:
   - BOL format: `^BOL-\d{4}-\d{6}$` (e.g., BOL-2026-000123)
   - Weight: `> 0` and `<= max_receipt_weight_lbs` (default: 100,000 lbs)
   - Material type: Must be selected

### Resolution
1. **BOL Format Error**:
   - Verify BOL matches pattern: `BOL-YYYY-NNNNNN`
   - Example valid: `BOL-2026-000123`
   - Example invalid: `BOL-2026-123` (too short)

2. **Weight Error**:
   - Ensure weight > 0
   - Check if weight exceeds `itad_core.max_receipt_weight_lbs`
   - For heavy loads, increase max weight parameter

3. **Material Type Missing**:
   - Select material type from dropdown
   - Phase 2.3 will sync taxonomy from ITAD Core

---

## Capturing Evidence for Audit

### Export Audit Logs
1. Navigate to: Technical → Database Structure → Models → `itad.receipt.audit.log`
2. Apply filters:
   - Date range: `attempted_at >= YYYY-MM-DD`
   - Outcome: Select specific outcome (e.g., `API_UNREACHABLE`)
   - User: Filter by specific user
   - Order: Filter by FSM order
3. Export: Action → Export → Select fields → Download CSV

### Audit Log Retention
- **Default Retention**: 180 days
- **Archiving**: Daily cron marks old logs as `archived = True`
- **Configuration**: `itad_core.audit_retention_days` system parameter
- **Archived Logs**: Remain in database but marked for potential cleanup

### Key Fields for Evidence
- `attempted_at`: When attempt occurred
- `outcome`: Result code (SUCCESS, API_UNREACHABLE, etc.)
- `error_message`: Detailed error description
- `idempotency_key`: Unique request identifier
- `correlation_id`: Request correlation ID
- `user_id`: Who attempted the receipt
- `order_id`: Which FSM order
- `manifest_no` / `bol_id`: Business identifiers

---

## Escalation Path

If troubleshooting steps do not resolve the issue:

1. **Gather Evidence**:
   - Export relevant audit logs
   - Screenshot error messages
   - Note FSM order ID and manifest number

2. **Check System Status**:
   - Verify ITAD Core service is running
   - Check recent system parameter changes
   - Review recent module upgrades

3. **Contact Support**:
   - Provide audit log export
   - Include error messages and timestamps
   - Specify affected orders/manifests
