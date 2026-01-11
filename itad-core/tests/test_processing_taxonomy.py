import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.db import async_session, create_tables
from app.main import app
from app.models.taxonomy import TaxonomyChangeLog
from app.schemas.processing import BatteryProcessingLineCreate, EwasteProcessingLineCreate


@pytest_asyncio.fixture(autouse=True)
async def ensure_taxonomy_tables():
    await create_tables()


def build_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


async def create_bol(client: AsyncClient) -> str:
    bol_number = f"TEST-BOL-{uuid.uuid4()}"
    data = {
        "bol_number": bol_number,
        "source_type": "DROP_OFF",
        "customer_snapshot_json": {"name": "Test Customer"},
    }
    headers = {"Idempotency-Key": f"bol-{uuid.uuid4()}"}
    response = await client.post("/api/v1/bol", json=data, headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


async def create_taxonomy_type(client: AsyncClient, group_code: str, type_code: str) -> dict:
    payload = {
        "group_code": group_code,
        "type_code": type_code,
        "type_name": f"{type_code} Name",
        "effective_from": datetime.utcnow().isoformat(),
    }
    headers = {
        "Idempotency-Key": f"tax-type-{uuid.uuid4()}",
        "X-Internal-Role": "compliance_admin",
    }
    response = await client.post("/api/v1/taxonomy/types", json=payload, headers=headers)
    assert response.status_code == 200
    return response.json()


async def create_taxonomy_item(client: AsyncClient, taxonomy_type_id: str, variant_code: str, sb20_flag: bool) -> dict:
    payload = {
        "taxonomy_type_id": taxonomy_type_id,
        "variant_code": variant_code,
        "variant_name": f"{variant_code} Name",
        "sb20_flag": sb20_flag,
        "effective_from": datetime.utcnow().isoformat(),
    }
    headers = {
        "Idempotency-Key": f"tax-item-{uuid.uuid4()}",
        "X-Internal-Role": "compliance_admin",
    }
    response = await client.post("/api/v1/taxonomy/items", json=payload, headers=headers)
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_processing_line_requires_taxonomy_item_id():
    async with build_client() as client:
        bol_id = await create_bol(client)
        payload = {
            "bol_id": bol_id,
            "started_at": datetime.utcnow().isoformat(),
            "lines": [
                {
                    "weight_lbs": 10.0,
                    "quantity": 1,
                }
            ],
        }
        response = await client.post(
            "/api/v1/battery-processing-sessions",
            json=payload,
            headers={"Idempotency-Key": f"battery-missing-tax-{uuid.uuid4()}"},
        )
        assert response.status_code == 422


def test_processing_schema_has_no_free_text_categories():
    assert "taxonomy_item_id" in BatteryProcessingLineCreate.model_fields
    assert "taxonomy_item_id" in EwasteProcessingLineCreate.model_fields
    assert "category_name" not in BatteryProcessingLineCreate.model_fields
    assert "category_name" not in EwasteProcessingLineCreate.model_fields


@pytest.mark.asyncio
async def test_taxonomy_governance_and_change_log():
    async with build_client() as client:
        type_code = f"EWASTE_{uuid.uuid4().hex[:8]}"
        taxonomy_type = await create_taxonomy_type(client, "INBOUND", type_code)
        taxonomy_item = await create_taxonomy_item(
            client, taxonomy_type["id"], f"CRT_{uuid.uuid4().hex[:6]}", sb20_flag=True
        )

        delete_response = await client.delete("/api/v1/taxonomy/types")
        assert delete_response.status_code == 405

        put_response = await client.put(
            "/api/v1/taxonomy/types",
            json={"type_code": "NEW_CODE"},
        )
        assert put_response.status_code == 405

    async with async_session() as session:
        result = await session.execute(
            select(TaxonomyChangeLog).where(
                TaxonomyChangeLog.entity_id.in_([taxonomy_type["id"], taxonomy_item["id"]])
            )
        )
        logs = result.scalars().all()
        assert len(logs) >= 2
        assert all(log.action_type == "CREATE" for log in logs)


@pytest.mark.asyncio
async def test_headcount_required_for_ewaste_session():
    async with build_client() as client:
        bol_id = await create_bol(client)
        type_code = f"EWASTE_{uuid.uuid4().hex[:8]}"
        taxonomy_type = await create_taxonomy_type(client, "INBOUND", type_code)
        taxonomy_item = await create_taxonomy_item(
            client, taxonomy_type["id"], f"LCD_{uuid.uuid4().hex[:6]}", sb20_flag=True
        )

        payload = {
            "bol_id": bol_id,
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "lines": [
                {
                    "taxonomy_item_id": taxonomy_item["id"],
                    "weight_lbs": 50.0,
                    "quantity": 1,
                }
            ],
        }
        response = await client.post(
            "/api/v1/ewaste-processing-sessions",
            json=payload,
            headers={"Idempotency-Key": f"ewaste-missing-headcount-{uuid.uuid4()}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_sb20_flag_filtering():
    async with build_client() as client:
        type_code = f"EWASTE_{uuid.uuid4().hex[:8]}"
        taxonomy_type = await create_taxonomy_type(client, "INBOUND", type_code)
        await create_taxonomy_item(client, taxonomy_type["id"], f"CRT_{uuid.uuid4().hex[:6]}", sb20_flag=True)
        await create_taxonomy_item(client, taxonomy_type["id"], f"MIX_{uuid.uuid4().hex[:6]}", sb20_flag=False)

        response = await client.get(
            f"/api/v1/taxonomy/items?group_code=INBOUND&type_code={type_code}&sb20_flag=true"
        )
        assert response.status_code == 200
        items = response.json()
        assert items
        assert all(item["sb20_flag"] is True for item in items)
