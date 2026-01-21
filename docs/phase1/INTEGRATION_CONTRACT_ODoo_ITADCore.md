# Integration Contract: Odoo 18 ↔ ITAD Core

**Version**: 1.0  
**Last Updated**: 2026-01-17  
**Status**: Active

## Overview

This document defines the integration contract between Odoo 18 Field Service and ITAD Core for receiving weight record creation.

## System of Record (SoR) Boundaries

- **Odoo 18**: SoR for dispatch scheduling and operational state
- **ITAD Core**: SoR for compliance data (pickup manifests, BOLs, receiving weight records)

**Critical Rule**: Odoo triggers creation via API; ITAD Core owns immutable records.

---

## API Endpoint: Create Receiving Weight Record

### Request

**Method**: `POST`  
**Path**: `/api/v1/receiving-weight-records`  
**Content-Type**: `application/json`

**Headers** (Required):
```
Idempotency-Key: receipt-{uuid}
X-Correlation-Id: corr-receipt-{uuid}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Schema**:
```json
{
  "bol_id": "string (required, format: BOL-YYYY-NNNNNN)",
  "occurred_at": "string (required, ISO 8601 datetime)",
  "material_received_as": "string (required, material type code)",
  "container_type": "string (required, enum: PALLET|GAYLORD|DRUM|BOX|BULK)",
  "quantity": "integer (required, > 0)",
  "gross_weight": "number (required, > 0)",
  "tare_weight": "number (required, >= 0)",
  "net_weight": "number (required, > 0)",
  "weight_unit": "string (required, enum: LBS|KG)",
  "scale_id": "string (required)",
  "ddr_status": "boolean (required)",
  "receiver_employee_id": "string (required)",
  "receiver_name": "string (required)",
  "receiver_signature_json": "object (required)",
  "tare_source": "string (required, enum: NONE|MANUAL|SCALE|DATABASE)",
  "notes": "string (optional)"
}
```

**Field Constraints**:
- `bol_id`: Must match pattern `^BOL-\d{4}-\d{6}$`
- `gross_weight`, `net_weight`: Must be > 0
- `tare_weight`: Must be >= 0
- `quantity`: Must be > 0
- `receiver_signature_json`: Must contain `{"type": "string", "user_id": integer, "timestamp": "ISO 8601"}`

**Forbidden Fields** (must NOT be included):
- `id` (server-generated)
- `created_at` (server-generated)
- `updated_at` (server-generated)
- `created_by` (server-generated)

### Response

**Success (201 Created)**:
```json
{
  "id": "string (UUID or integer)",
  "bol_id": "string",
  "occurred_at": "string (ISO 8601)",
  "material_received_as": "string",
  "container_type": "string",
  "quantity": "integer",
  "gross_weight": "number",
  "tare_weight": "number",
  "net_weight": "number",
  "weight_unit": "string",
  "scale_id": "string",
  "ddr_status": "boolean",
  "receiver_employee_id": "string",
  "receiver_name": "string",
  "receiver_signature_json": "object",
  "tare_source": "string",
  "notes": "string",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

**Error Responses**:

**400 Bad Request** - Validation error:
```json
{
  "detail": "string (error message)"
}
```

**422 Unprocessable Entity** - Schema validation error:
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

**500 Internal Server Error**:
```json
{
  "detail": "string (error message)"
}
```

---

## API Health Check

### Endpoint: Health Check

**Method**: `GET`  
**Path**: `/health`  
**Response** (200 OK):
```json
{
  "status": "healthy"
}
```

### Endpoint: OpenAPI Schema

**Method**: `GET`  
**Path**: `/openapi.json`  
**Response** (200 OK):
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "string",
    "version": "string"
  },
  ...
}
```

---

## Idempotency Behavior

**Idempotency-Key Header**:
- Format: `receipt-{uuid}`
- Stable across retries (never regenerated)
- ITAD Core returns cached response for duplicate keys within 24 hours

**Duplicate Detection**:
- Same `Idempotency-Key` → Returns existing record (200 OK)
- Different key, same `bol_id` + `occurred_at` → May create duplicate (application logic dependent)

---

## Error Handling Contract

**Network Errors**:
- Odoo must retry with same `Idempotency-Key`
- Odoo must log attempt in audit trail

**Validation Errors (422)**:
- Odoo must NOT retry automatically
- Odoo must display error to user
- Odoo must log attempt with error details

**Server Errors (500)**:
- Odoo may retry with same `Idempotency-Key`
- Odoo must implement exponential backoff
- Odoo must log all attempts

---

## Version Compatibility

**Minimum ITAD Core Version**: 1.0.0  
**Supported Versions**: 1.x.x

**Version Detection**:
- Check `/openapi.json` → `info.version`
- Block submission if version < 1.0.0

---

## Rate Limiting

**ITAD Core Limits**:
- 100 requests per minute per API key
- 429 Too Many Requests response if exceeded

**Odoo Client-Side Limits** (recommended):
- Max 10 receipt attempts per hour per user/order combination
- Prevents accidental spam

---

## Test Scenarios

### Valid Request Example
```json
{
  "bol_id": "BOL-2026-000123",
  "occurred_at": "2026-01-17T19:30:00Z",
  "material_received_as": "EW-CPU-001",
  "container_type": "PALLET",
  "quantity": 1,
  "gross_weight": 150.5,
  "tare_weight": 0.0,
  "net_weight": 150.5,
  "weight_unit": "LBS",
  "scale_id": "DOCK-SCALE-01",
  "ddr_status": false,
  "receiver_employee_id": "42",
  "receiver_name": "John Doe",
  "receiver_signature_json": {
    "type": "odoo_user",
    "user_id": 42,
    "timestamp": "2026-01-17T19:30:00Z"
  },
  "tare_source": "NONE",
  "notes": "Received in good condition"
}
```

### Invalid Request Examples

**Missing Required Field**:
```json
{
  "bol_id": "BOL-2026-000123",
  // missing occurred_at
  ...
}
```
**Response**: 422 Unprocessable Entity

**Invalid BOL Format**:
```json
{
  "bol_id": "BOL-2026-123",  // too short
  ...
}
```
**Response**: 422 Unprocessable Entity

**Negative Weight**:
```json
{
  ...
  "gross_weight": -10.5,
  ...
}
```
**Response**: 422 Unprocessable Entity

---

## Change Log

**v1.0.0** (2026-01-17):
- Initial contract definition
- POST /api/v1/receiving-weight-records endpoint
- Idempotency requirements
- Error handling specifications
