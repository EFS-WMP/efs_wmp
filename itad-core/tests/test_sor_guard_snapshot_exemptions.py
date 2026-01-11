"""
Test SoR Guard behavior with snapshot field exemptions.

The SoR guard must:
1. Reject forbidden operational-truth keys at top level
2. Reject forbidden keys nested under non-snapshot fields
3. ALLOW forbidden keys inside snapshot_json or *_snapshot_json fields
"""
import hashlib
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


def build_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def build_valid_payload(**overrides):
    """Base valid payload for testing."""
    payload = {
        "source_system": "odoo18",
        "manifest_fingerprint": _fingerprint(f"mf-{uuid.uuid4().hex}"),
        "completed_at": "2026-01-02T03:04:05+00:00",
        "odoo_refs": {
            "odoo_day_route_id": f"route-{uuid.uuid4().hex[:6]}",
            "odoo_stop_id": f"stop-{uuid.uuid4().hex[:6]}",
            "odoo_pickup_occurrence_id": f"pickup-{uuid.uuid4().hex[:6]}",
            "odoo_work_order_id": f"wo-{uuid.uuid4().hex[:6]}",
            "customer_id": f"cust-{uuid.uuid4().hex[:6]}",
            "service_location_id": f"loc-{uuid.uuid4().hex[:6]}",
        },
        "route_snapshot_json": {
            "fsm_order_id": "order-001",
            "fsm_stage": "COMPLETED",
        },
        "location_snapshot_json": {
            "name": "Test Location",
            "street": "123 Main St",
        },
        "pod_evidence": [
            {
                "ref": "odoo-attachment:pod-1",
                "sha256": _fingerprint("pod-1"),
                "filename": "pod.jpg",
            }
        ],
    }
    payload.update(overrides)
    return payload


# ============================================================================
# Test 1: Forbidden key at top level is rejected
# ============================================================================
@pytest.mark.asyncio
async def test_forbidden_key_at_top_level_is_rejected():
    """
    Requirement: API must reject operational-truth fields at root level.
    Example: { "dispatch_status": "READY", ... }
    Expected: 422 with error mentioning the forbidden field.
    """
    payload = build_valid_payload()
    payload["dispatch_status"] = "READY"  # Forbidden at root
    
    async with build_client() as client:
        response = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": f"idem-toplevel-{uuid.uuid4().hex[:8]}"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        detail = response.json()["detail"]
        assert "dispatch_status" in detail.lower() or "operational truth" in detail.lower()


# ============================================================================
# Test 2: Forbidden key inside route_snapshot_json is ALLOWED
# ============================================================================
@pytest.mark.asyncio
async def test_forbidden_key_inside_route_snapshot_json_is_allowed():
    """
    Requirement: Snapshot fields are read-only archives; they may contain any data.
    Example: { "route_snapshot_json": { "route_state": "COMPLETED" } }
    Expected: 200 OK (route_state is allowed inside snapshot).
    """
    payload = build_valid_payload()
    # Add route_state (forbidden normally) but INSIDE route_snapshot_json
    payload["route_snapshot_json"]["route_state"] = "COMPLETED"
    payload["route_snapshot_json"]["stop_sequence"] = 1
    payload["route_snapshot_json"]["dispatch_status"] = "DISPATCHED"
    
    async with build_client() as client:
        response = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": f"idem-snapshot-{uuid.uuid4().hex[:8]}"}
        )
        assert response.status_code == 200, \
            f"Expected 200 (snapshot exemption), got {response.status_code}: {response.json()}"
        assert response.json()["status"] == "SUBMITTED"


# ============================================================================
# Test 3: Forbidden key inside location_snapshot_json is ALLOWED
# ============================================================================
@pytest.mark.asyncio
async def test_forbidden_key_inside_location_snapshot_json_is_allowed():
    """
    Requirement: location_snapshot_json is exempt from forbidden-field scanning.
    Example: { "location_snapshot_json": { "actual_arrival": "..." } }
    Expected: 200 OK.
    """
    payload = build_valid_payload()
    # Add actual_arrival (forbidden normally) but INSIDE location_snapshot_json
    payload["location_snapshot_json"]["actual_arrival"] = "2026-01-02T10:00:00+00:00"
    payload["location_snapshot_json"]["eta"] = "2026-01-02T10:30:00+00:00"
    
    async with build_client() as client:
        response = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": f"idem-locsnap-{uuid.uuid4().hex[:8]}"}
        )
        assert response.status_code == 200, \
            f"Expected 200 (snapshot exemption), got {response.status_code}: {response.json()}"


# ============================================================================
# Test 4: Forbidden key nested under non-snapshot field is rejected
# ============================================================================
@pytest.mark.asyncio
async def test_forbidden_key_nested_under_non_snapshot_is_rejected():
    """
    Requirement: Forbidden keys are still forbidden if nested under non-snapshot fields.
    Example: { "odoo_refs": { "dispatch_status": "READY" } }
    Expected: 422.
    """
    payload = build_valid_payload()
    # Inject forbidden field inside odoo_refs (non-snapshot)
    payload["odoo_refs"]["dispatch_status"] = "READY"
    
    async with build_client() as client:
        response = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": f"idem-nested-{uuid.uuid4().hex[:8]}"}
        )
        assert response.status_code == 422, \
            f"Expected 422 (nested forbidden), got {response.status_code}: {response.json()}"
        detail = response.json()["detail"]
        assert "dispatch_status" in detail.lower() or "operational truth" in detail.lower()


# ============================================================================
# Test 5: Multiple forbidden keys in different snapshot fields are allowed
# ============================================================================
@pytest.mark.asyncio
async def test_multiple_forbidden_keys_in_multiple_snapshots_allowed():
    """
    Requirement: Multiple snapshot fields can each contain forbidden keys.
    Expected: 200 OK (all are inside snapshots).
    """
    payload = build_valid_payload()
    # Populate snapshots with multiple forbidden terms
    payload["route_snapshot_json"]["route_state"] = "COMPLETED"
    payload["route_snapshot_json"]["dispatch_status"] = "DISPATCHED"
    payload["route_snapshot_json"]["eta"] = "2026-01-02T10:00:00+00:00"
    
    payload["location_snapshot_json"]["actual_arrival"] = "2026-01-02T10:05:00+00:00"
    payload["location_snapshot_json"]["driver_assignment"] = "driver-123"
    
    async with build_client() as client:
        response = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": f"idem-multi-{uuid.uuid4().hex[:8]}"}
        )
        assert response.status_code == 200, \
            f"Expected 200 (all snapshots), got {response.status_code}: {response.json()}"
        assert response.json()["status"] == "SUBMITTED"
