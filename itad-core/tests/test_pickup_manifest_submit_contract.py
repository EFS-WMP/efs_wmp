import hashlib
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
    return hashlib.sha256(value.encode()).hexdigest()


def build_payload(**overrides):
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
        "route_snapshot_json": {"route_state": "COMPLETED"},
        "location_snapshot_json": {"geocode_confidence": 0.9, "address": "123 Main St"},
        "pod_evidence": [
            {
                "ref": "s3://bucket/pod-1.jpg",
                "sha256": _fingerprint("pod-1"),
                "filename": "pod-1.jpg",
            }
        ],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_submit_requires_idempotency_key_header():
    async with build_client() as client:
        payload = build_payload()
        response = await client.post("/api/v1/pickup-manifests:submit", json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "Idempotency-Key header required"


@pytest.mark.asyncio
async def test_submit_is_idempotent_same_key_returns_same_ids_and_logs_duplicate_attempt():
    payload = build_payload()
    idempotency_key = f"idem-{uuid.uuid4().hex}"
    headers = {"Idempotency-Key": idempotency_key}

    async with build_client() as client:
        response1 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response1.status_code == 200
        data1 = response1.json()

        response2 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response2.status_code == 200
        data2 = response2.json()

    assert data1["pickup_manifest_id"] == data2["pickup_manifest_id"]
    assert data1["bol_id"] == data2["bol_id"]
    assert data1["manifest_no"] == data2["manifest_no"]

    async with async_session() as session:
        attempts = await session.execute(
            select(PickupManifestIntegrationAttempt).where(
                PickupManifestIntegrationAttempt.idempotency_key == idempotency_key
            )
        )
        outcomes = [row.outcome for row in attempts.scalars().all()]
        assert "ACCEPTED" in outcomes
        assert "DUPLICATE_RETURNED" in outcomes

        manifests = await session.execute(
            select(PickupManifest).where(
                PickupManifest.manifest_fingerprint == payload["manifest_fingerprint"]
            )
        )
        assert len(manifests.scalars().all()) == 1


@pytest.mark.asyncio
async def test_submit_dedupes_by_manifest_fingerprint_even_if_key_diff():
    payload = build_payload()
    headers1 = {"Idempotency-Key": f"idem-{uuid.uuid4().hex}"}
    headers2 = {"Idempotency-Key": f"idem-{uuid.uuid4().hex}"}

    async with build_client() as client:
        response1 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers1)
        assert response1.status_code == 200
        data1 = response1.json()

        response2 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers2)
        assert response2.status_code == 200
        data2 = response2.json()

    assert data1["pickup_manifest_id"] == data2["pickup_manifest_id"]
    assert data1["bol_id"] == data2["bol_id"]

    async with async_session() as session:
        attempts = await session.execute(
            select(PickupManifestIntegrationAttempt).where(
                PickupManifestIntegrationAttempt.manifest_fingerprint == payload["manifest_fingerprint"]
            )
        )
        outcomes = [row.outcome for row in attempts.scalars().all()]
        assert "ACCEPTED" in outcomes
        assert "DUPLICATE_RETURNED" in outcomes


@pytest.mark.asyncio
async def test_submit_creates_pickup_bol_bound_1_to_1():
    payload = build_payload()
    headers = {"Idempotency-Key": f"idem-{uuid.uuid4().hex}"}

    async with build_client() as client:
        response = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()

    async with async_session() as session:
        bols = await session.execute(
            select(BOL).where(BOL.pickup_manifest_id == data["pickup_manifest_id"])
        )
        bol_rows = bols.scalars().all()
        assert len(bol_rows) == 1
        assert bol_rows[0].source_type == SourceType.PICKUP.value


@pytest.mark.asyncio
async def test_get_manifest_returns_status_and_nullable_receiving_id():
    payload = build_payload()
    headers = {"Idempotency-Key": f"idem-{uuid.uuid4().hex}"}

    async with build_client() as client:
        response = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response.status_code == 200
        manifest_id = response.json()["pickup_manifest_id"]

        get_response = await client.get(f"/api/v1/pickup-manifests/{manifest_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["status"] == "BOUND_TO_BOL"
        assert data["receiving_id"] is None
