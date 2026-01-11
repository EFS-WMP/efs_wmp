import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import async_session
from app.models.external_ids import ExternalIDMap
from app.models.bol_stage_gates import BolGateType
from app.models.workstreams import WorkstreamType, WorkstreamStatus


def build_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_create_bol_idempotent():
    async with build_client() as client:
        data = {
            "bol_number": f"TEST-BOL-{uuid.uuid4()}",
            "source_type": "DROP_OFF",
            "customer_snapshot_json": {"name": "Test Customer"}
        }
        headers = {"Idempotency-Key": f"test-key-{uuid.uuid4()}"}

        # First request
        response1 = await client.post("/api/v1/bol", json=data, headers=headers)
        assert response1.status_code == 200
        result1 = response1.json()

        # Second request with same key
        response2 = await client.post("/api/v1/bol", json=data, headers=headers)
        assert response2.status_code == 200
        result2 = response2.json()

        # Should return same result
        assert result1["id"] == result2["id"]


@pytest.mark.asyncio
async def test_bol_uniqueness():
    async with build_client() as client:
        data = {
            "bol_number": f"UNIQUE-BOL-{uuid.uuid4()}",
            "source_type": "DROP_OFF",
            "customer_snapshot_json": {"name": "Test Customer"}
        }
        headers1 = {"Idempotency-Key": f"unique-key-{uuid.uuid4()}"}
        headers2 = {"Idempotency-Key": f"unique-key-{uuid.uuid4()}"}

        # First request
        response1 = await client.post("/api/v1/bol", json=data, headers=headers1)
        assert response1.status_code == 200

        # Second request with same bol_number
        response2 = await client.post("/api/v1/bol", json=data, headers=headers2)
        assert response2.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_bol_auto_generation():
    async with build_client() as client:
        data = {
            "source_type": "DROP_OFF",
            "customer_snapshot_json": {"name": "Test Customer"}
        }
        headers = {"Idempotency-Key": f"auto-gen-key-{uuid.uuid4()}"}

        response = await client.post("/api/v1/bol", json=data, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert "bol_number" in result
        assert result["bol_number"].startswith("BOL-MAIN-2026-")  # Assuming year 2026


@pytest.mark.asyncio
async def test_requirement_profile_persistence():
    async with build_client() as client:
        data = {
            "bol_number": f"PROFILE-BOL-{uuid.uuid4()}",
            "source_type": "DROP_OFF",
            "customer_snapshot_json": {"name": "Test Customer"},
            "requirement_profile_snapshot_json": {"rules": ["rule1"]},
            "requirement_profile_version": "v1.0",
            "requirement_profile_effective_from": "2026-01-01T00:00:00Z"
        }
        headers = {"Idempotency-Key": f"profile-key-{uuid.uuid4()}"}

        response = await client.post("/api/v1/bol", json=data, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["requirement_profile_snapshot_json"] == {"rules": ["rule1"]}
        assert result["requirement_profile_version"] == "v1.0"
        assert result["requirement_profile_effective_from"] is not None


@pytest.mark.asyncio
async def test_external_id_map_uniqueness():
    # Test via DB since no API yet
    async with async_session() as db:
        try:
            # Insert first
            map1 = ExternalIDMap(
                system="odoo",
                entity_type="work_order",
                external_id=f"wo-{uuid.uuid4()}",
                itad_entity_id=str(uuid.uuid4())
            )
            db.add(map1)
            await db.commit()

            # Try duplicate
            map2 = ExternalIDMap(
                system="odoo",
                entity_type="work_order",
                external_id=map1.external_id,
                itad_entity_id=str(uuid.uuid4())
            )
            db.add(map2)
            with pytest.raises(Exception):  # IntegrityError
                await db.commit()
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_bol_gate_append_only():
    async with build_client() as client:
        # Create BOL
        data = {"source_type": "DROP_OFF", "customer_snapshot_json": {"name": "Test"}}
        headers = {"Idempotency-Key": f"gate-test-key-{uuid.uuid4()}"}
        response = await client.post("/api/v1/bol", json=data, headers=headers)
        bol_id = response.json()["id"]

        # Append gate
        gate_data = {"gate_type": "REQUIREMENTS_CONFIRMED"}
        gate_headers = {"Idempotency-Key": f"gate-key-{uuid.uuid4()}"}
        gate_response = await client.post(f"/api/v1/bol/{bol_id}/gates", json=gate_data, headers=gate_headers)
        assert gate_response.status_code == 200

        # Invalid transition
        invalid_gate = {"gate_type": "BOL_CLOSED"}
        invalid_response = await client.post(
            f"/api/v1/bol/{bol_id}/gates",
            json=invalid_gate,
            headers={"Idempotency-Key": f"invalid-key-{uuid.uuid4()}"},
        )
        assert invalid_response.status_code == 422


@pytest.mark.asyncio
async def test_requirements_confirm_and_lock():
    async with build_client() as client:
        # Create BOL
        data = {"source_type": "DROP_OFF", "customer_snapshot_json": {"name": "Test"}}
        headers = {"Idempotency-Key": f"req-test-key-{uuid.uuid4()}"}
        response = await client.post("/api/v1/bol", json=data, headers=headers)
        bol_id = response.json()["id"]

        # Confirm requirements
        req_data = {"requires_battery_processing": True, "requires_ewaste_processing": False, "rationale": "test"}
        req_headers = {"Idempotency-Key": f"req-key-{uuid.uuid4()}"}
        req_response = await client.post(f"/api/v1/bol/{bol_id}/requirements/confirm", json=req_data, headers=req_headers)
        assert req_response.status_code == 200

        # Try to confirm again
        req_response2 = await client.post(
            f"/api/v1/bol/{bol_id}/requirements/confirm",
            json=req_data,
            headers={"Idempotency-Key": f"req-key2-{uuid.uuid4()}"},
        )
        assert req_response2.status_code == 409


@pytest.mark.asyncio
async def test_close_bol_with_blockers():
    async with build_client() as client:
        # Create BOL
        data = {"source_type": "DROP_OFF", "customer_snapshot_json": {"name": "Test"}}
        headers = {"Idempotency-Key": f"close-test-key-{uuid.uuid4()}"}
        response = await client.post("/api/v1/bol", json=data, headers=headers)
        bol_id = response.json()["id"]

        # Try to close without requirements
        close_headers = {"Idempotency-Key": f"close-key-{uuid.uuid4()}"}
        close_response = await client.post(f"/api/v1/bol/{bol_id}/close", headers=close_headers)
        assert close_response.status_code == 409
        assert "requirements_not_confirmed" in close_response.json()["detail"]
