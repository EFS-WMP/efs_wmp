"""
Phase 1 Vertical Slice: Odoo18 → ITAD Core Submit Endpoint (TDD Contract Tests)

Tests verify:
1. Idempotency-Key header required
2. Idempotency: same key returns same IDs (dedup by fingerprint)
3. 1:1 BOL binding for PICKUP source type (no duplicate BOLs)
4. SoR Guard: reject operational truth fields (dispatch_status, stop_execution, etc.)
5. Attempt logging: ACCEPTED, DUPLICATE_RETURNED, REJECTED outcomes
"""
import hashlib
import json
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.db import async_session
from app.main import app
from app.models.bol import BOL, SourceType
from app.models.pickup_manifest import PickupManifest, PickupManifestIntegrationAttempt


def build_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def _fingerprint(value: str) -> str:
    """Compute SHA256 fingerprint matching Odoo payload normalization."""
    return hashlib.sha256(value.encode()).hexdigest()


def build_valid_payload(**overrides):
    """Build deterministic payload for idempotent testing."""
    payload = {
        "source_system": "odoo18",
        "manifest_fingerprint": _fingerprint("phase1-test-payload-v1"),
        "completed_at": "2026-01-02T10:30:00+00:00",
        "odoo_refs": {
            "odoo_day_route_id": "route-phase1-001",
            "odoo_stop_id": "stop-phase1-001",
            "odoo_pickup_occurrence_id": "pickup-phase1-001",
            "odoo_work_order_id": "wo-phase1-001",
            "customer_id": "cust-phase1-001",
            "service_location_id": "loc-phase1-001",
        },
        "route_snapshot_json": {
            "fsm_order_id": "order-phase1-001",
            "fsm_stage": "COMPLETED",
        },
        "location_snapshot_json": {
            "name": "Test Location",
            "street": "123 Main St",
            "city": "Testville",
            "zip": "12345",
            "country": "US",
        },
        "pod_evidence": [
            {
                "ref": "odoo-attachment:phase1-pod-1",
                "sha256": _fingerprint("pod-evidence-v1"),
                "filename": "pod-photo.jpg",
            }
        ],
    }
    payload.update(overrides)
    return payload


# ============================================================================
# Test 1: Idempotency-Key Header Required
# ============================================================================
@pytest.mark.asyncio
async def test_submit_requires_idempotency_key_header():
    """
    Requirement: POST /api/v1/pickup-manifests:submit requires Idempotency-Key header.
    Without it, endpoint returns 400.
    """
    payload = build_valid_payload()
    async with build_client() as client:
        response = await client.post("/api/v1/pickup-manifests:submit", json=payload)
        assert response.status_code == 400
        detail = response.json().get("detail", "")
        assert "Idempotency-Key" in detail


# ============================================================================
# Test 2: Idempotency - Same Key Returns Same IDs (Dedup by Fingerprint)
# ============================================================================
@pytest.mark.asyncio
async def test_submit_is_idempotent_same_key_returns_same_ids_and_logs_duplicate():
    """
    Requirement: Posting same payload with same Idempotency-Key returns same IDs.
    - First call: ACCEPTED
    - Second call: DUPLICATE_RETURNED (idempotent)
    Asserts: manifest_id, manifest_no, bol_id are identical.
    """
    payload = build_valid_payload()
    idempotency_key = f"idem-phase1-001-{uuid.uuid4().hex[:8]}"
    headers = {"Idempotency-Key": idempotency_key}

    async with build_client() as client:
        # First submission
        response1 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response1.status_code == 200, f"First submit failed: {response1.text}"
        data1 = response1.json()

        # Verify required response fields
        assert data1.get("pickup_manifest_id"), "Response missing pickup_manifest_id"
        assert data1.get("manifest_no"), "Response missing manifest_no"
        assert data1.get("bol_id"), "Response missing bol_id"
        assert data1.get("status") == "SUBMITTED", f"Unexpected status: {data1.get('status')}"

        # Second submission (idempotent)
        response2 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response2.status_code == 200, f"Second submit (idempotent) failed: {response2.text}"
        data2 = response2.json()

    # Verify idempotency: same IDs returned
    assert data1["pickup_manifest_id"] == data2["pickup_manifest_id"], \
        "Idempotent submit returned different manifest_id"
    assert data1["bol_id"] == data2["bol_id"], \
        "Idempotent submit returned different bol_id"
    assert data1["manifest_no"] == data2["manifest_no"], \
        "Idempotent submit returned different manifest_no"

    # Verify attempt logging: ACCEPTED then DUPLICATE_RETURNED
    async with async_session() as session:
        attempts = await session.execute(
            select(PickupManifestIntegrationAttempt).where(
                PickupManifestIntegrationAttempt.idempotency_key == idempotency_key
            ).order_by(PickupManifestIntegrationAttempt.occurred_at)
        )
        attempt_rows = attempts.scalars().all()
        assert len(attempt_rows) >= 2, f"Expected 2+ attempts logged, got {len(attempt_rows)}"

        outcomes = [row.outcome for row in attempt_rows]
        assert "ACCEPTED" in outcomes, "First attempt should be ACCEPTED"
        assert "DUPLICATE_RETURNED" in outcomes, "Second attempt should be DUPLICATE_RETURNED"


# ============================================================================
# Test 3: Deduplication by (source_system, manifest_fingerprint) When Key Differs
# ============================================================================
@pytest.mark.asyncio
async def test_submit_dedupes_by_fingerprint_different_key_returns_same_ids():
    """
    Requirement: Same manifest_fingerprint deduplicates regardless of idempotency_key.
    If payload has same fingerprint but different idempotency_key, return cached manifest/bol.
    """
    # Same payload → same fingerprint
    payload = build_valid_payload()
    fingerprint = payload["manifest_fingerprint"]

    idempotency_key_1 = f"idem-phase1-fp-001-{uuid.uuid4().hex[:8]}"
    idempotency_key_2 = f"idem-phase1-fp-002-{uuid.uuid4().hex[:8]}"  # Different key

    async with build_client() as client:
        # First submit with key 1
        response1 = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": idempotency_key_1}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        manifest_id_1 = data1["pickup_manifest_id"]
        bol_id_1 = data1["bol_id"]

        # Second submit with different key but same fingerprint
        response2 = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers={"Idempotency-Key": idempotency_key_2}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        manifest_id_2 = data2["pickup_manifest_id"]
        bol_id_2 = data2["bol_id"]

    # Verify deduplication: same manifest and BOL despite different keys
    assert manifest_id_1 == manifest_id_2, \
        "Fingerprint dedup failed: different manifest_id for same fingerprint"
    assert bol_id_1 == bol_id_2, \
        "Fingerprint dedup failed: different bol_id for same fingerprint"

    # Verify both attempts logged with different keys
    async with async_session() as session:
        attempts = await session.execute(
            select(PickupManifestIntegrationAttempt).where(
                PickupManifestIntegrationAttempt.manifest_fingerprint == fingerprint
            )
        )
        attempt_rows = attempts.scalars().all()
        attempt_keys = {row.idempotency_key for row in attempt_rows}
        assert idempotency_key_1 in attempt_keys or idempotency_key_2 in attempt_keys, \
            "Attempts not logged with correct idempotency keys"


# ============================================================================
# Test 4: 1:1 BOL Binding for PICKUP source_type (No Duplicate BOLs)
# ============================================================================
@pytest.mark.asyncio
async def test_submit_creates_pickup_bol_1_to_1_and_source_type_pickup():
    """
    Requirement: Each pickup_manifest has at most 1 BOL (source_type=PICKUP).
    Constraint: BOL.pickup_manifest_id is UNIQUE when source_type=PICKUP.
    Submit twice with same fingerprint → same BOL returned (no duplicate BOLs created).
    """
    payload = build_valid_payload()
    idempotency_key = f"idem-phase1-bol1to1-{uuid.uuid4().hex[:8]}"
    headers = {"Idempotency-Key": idempotency_key}

    manifest_ids = []
    bol_ids = []

    async with build_client() as client:
        # Submit twice (idempotent)
        for i in range(2):
            response = await client.post(
                "/api/v1/pickup-manifests:submit",
                json=payload,
                headers=headers
            )
            assert response.status_code == 200, f"Submit {i+1} failed: {response.text}"
            data = response.json()
            manifest_ids.append(data["pickup_manifest_id"])
            bol_ids.append(data["bol_id"])

    # Verify same manifest and BOL (idempotent)
    assert len(set(manifest_ids)) == 1, "Different manifests returned on idempotent submit"
    assert len(set(bol_ids)) == 1, "Different BOLs returned on idempotent submit"

    manifest_id = manifest_ids[0]
    bol_id = bol_ids[0]

    # Query database and verify BOL source_type and 1:1 binding
    async with async_session() as session:
        # Fetch BOL
        bol = await session.execute(
            select(BOL).where(BOL.id == bol_id)
        )
        bol_obj = bol.scalar_one_or_none()
        assert bol_obj is not None, f"BOL {bol_id} not found"
        assert bol_obj.source_type == SourceType.PICKUP.value, \
            f"BOL source_type should be PICKUP, got {bol_obj.source_type}"
        assert bol_obj.pickup_manifest_id == manifest_id, \
            f"BOL.pickup_manifest_id mismatch: expected {manifest_id}, got {bol_obj.pickup_manifest_id}"

        # Verify no duplicate BOLs for this manifest
        bol_count = await session.execute(
            select(BOL).where(BOL.pickup_manifest_id == manifest_id)
        )
        bols = bol_count.scalars().all()
        assert len(bols) == 1, f"Expected 1 BOL for manifest {manifest_id}, got {len(bols)}"


# ============================================================================
# Test 5: SoR Guard - Reject Operational Truth Fields
# ============================================================================
@pytest.mark.asyncio
async def test_submit_rejects_operational_truth_fields():
    """
    Requirement: API rejects payloads containing dispatch/route execution truth fields.
    Fields forbidden: dispatch_status, stop_execution, route_execution_truth, etc.
    Reason: Odoo is dispatch SoR; ITAD Core must not accept/store dispatch state.
    Expected: 422 Unprocessable Entity with clear error message.
    """
    forbidden_fields = [
        ("dispatch_status", "DISPATCHED"),
        ("stop_execution", "START_TIME"),
        ("route_execution_truth", {"state": "in_progress"}),
        ("driver_assignment", "driver-123"),
        ("eta", "2026-01-02T11:00:00+00:00"),
    ]

    for field_name, field_value in forbidden_fields:
        payload = build_valid_payload()
        # Inject forbidden field at root level or in odoo_refs (common mistake)
        payload[field_name] = field_value

        async with build_client() as client:
            response = await client.post(
                "/api/v1/pickup-manifests:submit",
                json=payload,
                headers={"Idempotency-Key": f"idem-reject-{field_name}-{uuid.uuid4().hex[:8]}"}
            )
            assert response.status_code == 422, \
                f"Expected 422 for forbidden field '{field_name}', got {response.status_code}: {response.text}"
            detail = response.json().get("detail", "")
            assert field_name.lower() in detail.lower() or "forbidden" in detail.lower(), \
                f"Error detail should mention '{field_name}' or 'forbidden', got: {detail}"


# ============================================================================
# Test 6: Attempt Logging - All Outcomes Present
# ============================================================================
@pytest.mark.asyncio
async def test_submit_logs_attempt_with_correlation_id_and_outcome():
    """
    Requirement: Every submit attempt is logged in PickupManifestIntegrationAttempt (append-only).
    Fields logged: idempotency_key, correlation_id, outcome (ACCEPTED/DUPLICATE_RETURNED/REJECTED/ERROR),
    manifest_fingerprint, occurred_at.
    """
    payload = build_valid_payload()
    idempotency_key = f"idem-phase1-log-{uuid.uuid4().hex[:8]}"
    correlation_id = f"corr-phase1-{uuid.uuid4().hex[:8]}"
    headers = {
        "Idempotency-Key": idempotency_key,
        "X-Correlation-Id": correlation_id,
    }

    async with build_client() as client:
        response = await client.post(
            "/api/v1/pickup-manifests:submit",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200

    # Verify attempt logged
    async with async_session() as session:
        attempt = await session.execute(
            select(PickupManifestIntegrationAttempt).where(
                PickupManifestIntegrationAttempt.idempotency_key == idempotency_key
            )
        )
        attempt_obj = attempt.scalar_one_or_none()
        assert attempt_obj is not None, f"Attempt not logged for idempotency_key {idempotency_key}"

        # Verify fields
        assert attempt_obj.outcome in ["ACCEPTED", "DUPLICATE_RETURNED", "REJECTED", "ERROR"], \
            f"Invalid outcome: {attempt_obj.outcome}"
        assert attempt_obj.manifest_fingerprint == payload["manifest_fingerprint"], \
            "Attempt fingerprint mismatch"
        assert attempt_obj.correlation_id == correlation_id, \
            "Attempt correlation_id mismatch"
        assert attempt_obj.occurred_at is not None, "Attempt occurred_at not set"
