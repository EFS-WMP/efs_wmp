# Phase 2.2 - Configurable Defaults

## System Parameters

Phase 2.2 introduces configurable defaults via `ir.config_parameter` to replace hardcoded values. All parameters are initialized idempotently via `post_init_hook`.

### Parameter Reference

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `itad_core.default_container_type` | `PALLET` | Default container type for receiving weight records |
| `itad_core.default_scale_id` | `DOCK-SCALE-01` | Default scale identifier for weight measurements |
| `itad_core.receipt_timeout_seconds` | `30` | HTTP timeout for ITAD Core API calls (seconds) |
| `itad_core.max_receipt_weight_lbs` | `100000` | Maximum allowed weight for receipt confirmation (lbs) |

### Configuration

To customize these values, navigate to:
**Settings → Technical → Parameters → System Parameters**

Or use the ORM:

```python
env["ir.config_parameter"].sudo().set_param("itad_core.default_container_type", "GAYLORD")
```

### Idempotency Key Retention Policy

**Critical**: The `original_idempotency_key` field is **never regenerated** across retries.

- **First attempt**: Generates unique key `receipt-{uuid}`
- **Retry attempts**: Reuse the same `original_idempotency_key`
- **Purpose**: Ensures ITAD Core can detect duplicate requests even after network failures

This guarantees that retrying a failed receipt confirmation will not create duplicate `receiving_weight_record` entries in ITAD Core.

### Validation Rules

#### BOL Format
- **Pattern**: `BOL-YYYY-NNNNNN`
- **Example**: `BOL-2026-000123`
- **Validation**: Regex `^BOL-\d{4}-\d{6}$`

#### Weight Validation
- **Minimum**: `> 0 lbs`
- **Maximum**: `<= max_receipt_weight_lbs` (default 100,000 lbs)
- **Precision**: 2 decimal places

### RBAC

Access to receiving confirmation is restricted to users in the **ITAD Receiving Manager** group (`itad_core.group_receiving_manager`).

To grant access:
1. Navigate to **Settings → Users & Companies → Users**
2. Edit user
3. Add to group: **ITAD Receiving Manager**

### Audit Logging

All receipt confirmation attempts (success and failure) are logged in the `itad.receipt.audit.log` model with:
- Attempt number
- Success/failure status
- Error message (if failed)
- ITAD Core response ID (if successful)
- Idempotency key
- Correlation ID
- Timestamp

### Migration Notes

**Upgrading from Phase 2.1**:
1. Existing system parameters are preserved (idempotent initialization)
2. New fields added to wizard (backward compatible)
3. Security group created automatically
4. Users must be manually added to receiving manager group

**Database Changes**:
- New model: `itad.receipt.audit.log`
- New wizard fields: `error_state`, `last_error_message`, `original_idempotency_key`, `attempt_count`, `last_attempt_at`, `successful_at`, `api_response_id`
- New security group: `itad_core.group_receiving_manager`
