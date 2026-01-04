import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.main import app
from app.core.config import settings
from app.models.receiving import ReceivingWeightRecordV3
from app.models.receiving_record_voids import ReceivingRecordVoid
from app.schemas.receiving import ReceivingWeightRecordV3Create, ReceivingRecordVoidCreate
from app.services.receiving_service import (
    create_receiving_weight_record,
    validate_tare_policy,
    validate_net_weight,
    void_receiving_record,
    reissue_receiving_record,
    get_receiving_record,
)


def build_record_payload(**overrides):
    payload = {
        "bol_id": "bol-123",
        "occurred_at": datetime.now().isoformat(),
        "material_received_as": "CHEMICAL_A",
        "container_type": "DRUM",
        "quantity": 1,
        "gross_weight": 100.0,
        "tare_weight": 10.0,
        "net_weight": 90.0,
        "weight_unit": "LBS",
        "scale_id": "scale-1",
        "un_number": None,
        "hazard_class": None,
        "ddr_status": True,
        "receiver_employee_id": "emp-123",
        "receiver_name": "John Doe",
        "receiver_signature_json": {"signature": "data", "timestamp": datetime.now().isoformat()},
        "tare_source": "MEASURED_ON_SCALE",
    }
    payload.update(overrides)
    return payload


def build_record_data(**overrides):
    return ReceivingWeightRecordV3Create(**build_record_payload(**overrides))


class TestReceivingService:
    @pytest.mark.asyncio
    async def test_create_receiving_weight_record_success(self, db_session: AsyncSession):
        record_data = build_record_data(
            tare_source="CONTAINER_TYPE_PROFILE_SNAPSHOT",
            tare_profile_snapshot_json={"profile_id": "profile-demo", "tare_weight": 10.0},
        )

        result = await create_receiving_weight_record(
            db_session, record_data, "test-user", "req-123", "corr-123"
        )

        assert result.bol_id == "bol-123"
        assert result.material_received_as == "CHEMICAL_A"
        assert result.tare_source == "CONTAINER_TYPE_PROFILE_SNAPSHOT"
        assert result.is_void is False

    @pytest.mark.asyncio
    async def test_validate_tare_policy_profile_required(self, db_session: AsyncSession):
        record_data = build_record_data(
            tare_source="CONTAINER_TYPE_PROFILE_SNAPSHOT",
            tare_profile_snapshot_json=None,
        )

        with pytest.raises(ValueError, match="tare_profile_snapshot_json required"):
            await validate_tare_policy(record_data)

    @pytest.mark.asyncio
    async def test_validate_net_weight_mismatch(self, db_session: AsyncSession):
        record_data = build_record_data(
            net_weight=95.0,
            tare_source="MANUAL_TARE_WITH_APPROVAL",
        )

        with pytest.raises(ValueError, match="Net weight mismatch"):
            await validate_net_weight(record_data)

    @pytest.mark.asyncio
    async def test_void_receiving_record(self, db_session: AsyncSession):
        record_data = build_record_data()

        created_record = await create_receiving_weight_record(
            db_session, record_data, "test-user", "req-123", "corr-123"
        )

        void_data = ReceivingRecordVoidCreate(
            receiving_record_id=created_record.id,
            void_reason="Data entry error",
            voided_by="admin",
        )

        void_result = await void_receiving_record(
            db_session, void_data, "req-456", "corr-456"
        )

        assert void_result.receiving_record_id == created_record.id
        assert void_result.void_reason == "Data entry error"

        void_entry = await db_session.execute(
            select(ReceivingRecordVoid).where(
                ReceivingRecordVoid.receiving_record_id == created_record.id
            )
        )
        assert void_entry.scalars().first() is not None

        stored_record = await db_session.get(ReceivingWeightRecordV3, created_record.id)
        assert stored_record.is_void is False
        assert stored_record.void_reason is None
        assert stored_record.voided_record_id is None

    @pytest.mark.asyncio
    async def test_reissue_receiving_record(self, db_session: AsyncSession):
        record_data = build_record_data()

        original_record = await create_receiving_weight_record(
            db_session, record_data, "test-user", "req-123", "corr-123"
        )

        void_data = ReceivingRecordVoidCreate(
            receiving_record_id=original_record.id,
            void_reason="Data entry error",
            voided_by="admin",
        )
        await void_receiving_record(db_session, void_data, "req-456", "corr-456")

        reissue_data = build_record_data(
            gross_weight=105.0,
            net_weight=95.0,
            receiver_name="Jane Doe",
            tare_source="MANUAL_TARE_WITH_APPROVAL",
        )

        reissued_record = await reissue_receiving_record(
            db_session, original_record.id, reissue_data, "test-user", "req-789", "corr-789"
        )

        assert reissued_record.reissue_of_id == original_record.id
        assert reissued_record.gross_weight == 105.0

    @pytest.mark.asyncio
    async def test_get_receiving_record_blind_mode(self, db_session: AsyncSession):
        record_data = build_record_data(
            declared_gross_weight=100.0,
            declared_tare_weight=10.0,
            declared_net_weight=90.0,
            declared_weight_source="SHIPPER_MANIFEST",
        )

        created_record = await create_receiving_weight_record(
            db_session, record_data, "test-user", "req-123", "corr-123"
        )

        blind_result = await get_receiving_record(
            db_session,
            created_record.id,
            blind_mode=True,
            include_declared=False,
        )
        assert blind_result.receiver_name == "John Doe"
        assert blind_result.declared_gross_weight is None
        assert blind_result.declared_weight_source is None

        unredacted_result = await get_receiving_record(
            db_session,
            created_record.id,
            blind_mode=True,
            include_declared=True,
        )
        assert unredacted_result.declared_gross_weight == 100.0
        assert unredacted_result.declared_weight_source == "SHIPPER_MANIFEST"


@pytest.mark.asyncio
async def test_receiving_required_fields_422():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        payload = build_record_payload()
        headers = {"Idempotency-Key": "recv-req-1"}

        missing_scale = payload.copy()
        missing_scale.pop("scale_id")
        response = await client.post(
            "/api/v1/receiving-weight-records",
            json=missing_scale,
            headers=headers,
        )
        assert response.status_code == 422

        missing_receiver = payload.copy()
        missing_receiver.pop("receiver_employee_id")
        response = await client.post(
            "/api/v1/receiving-weight-records",
            json=missing_receiver,
            headers={"Idempotency-Key": "recv-req-2"},
        )
        assert response.status_code == 422

        missing_ddr = payload.copy()
        missing_ddr.pop("ddr_status")
        response = await client.post(
            "/api/v1/receiving-weight-records",
            json=missing_ddr,
            headers={"Idempotency-Key": "recv-req-3"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_receiving_blind_redaction_and_admin_access():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        bol_payload = {
            "bol_number": "TEST-BOL-RECV-001",
            "source_type": "PICKUP",
            "customer_snapshot_json": {"name": "Test Customer"},
        }
        bol_response = await client.post(
            "/api/v1/bol",
            json=bol_payload,
            headers={"Idempotency-Key": "bol-recv-1"},
        )
        assert bol_response.status_code == 200
        bol_id = bol_response.json()["id"]

        record_payload = build_record_payload(
            bol_id=bol_id,
            declared_gross_weight=100.0,
            declared_tare_weight=10.0,
            declared_net_weight=90.0,
            declared_weight_source="SHIPPER_MANIFEST",
        )
        record_response = await client.post(
            "/api/v1/receiving-weight-records",
            json=record_payload,
            headers={"Idempotency-Key": "recv-1"},
        )
        assert record_response.status_code == 200
        record_id = record_response.json()["id"]

        original_setting = settings.blind_receiving
        settings.blind_receiving = True
        try:
            redacted_response = await client.get(
                f"/api/v1/receiving-weight-records/{record_id}"
            )
            assert redacted_response.status_code == 200
            redacted_data = redacted_response.json()
            assert "declared_gross_weight" not in redacted_data

            forbidden_response = await client.get(
                f"/api/v1/receiving-weight-records/{record_id}",
                params={"include_declared": "true"},
            )
            assert forbidden_response.status_code == 403

            admin_response = await client.get(
                f"/api/v1/receiving-weight-records/{record_id}",
                params={"include_declared": "true"},
                headers={"X-Internal-Role": "compliance_admin"},
            )
            assert admin_response.status_code == 200
            admin_data = admin_response.json()
            assert admin_data["declared_gross_weight"] == 100.0
        finally:
            settings.blind_receiving = original_setting


@pytest.mark.asyncio
async def test_receiving_no_update_delete_routes():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        bol_payload = {
            "bol_number": "TEST-BOL-RECV-002",
            "source_type": "PICKUP",
            "customer_snapshot_json": {"name": "Test Customer"},
        }
        bol_response = await client.post(
            "/api/v1/bol",
            json=bol_payload,
            headers={"Idempotency-Key": "bol-recv-2"},
        )
        assert bol_response.status_code == 200
        bol_id = bol_response.json()["id"]

        record_payload = build_record_payload(bol_id=bol_id)
        record_response = await client.post(
            "/api/v1/receiving-weight-records",
            json=record_payload,
            headers={"Idempotency-Key": "recv-2"},
        )
        assert record_response.status_code == 200
        record_id = record_response.json()["id"]

        put_response = await client.put(
            f"/api/v1/receiving-weight-records/{record_id}",
            json=record_payload,
        )
        assert put_response.status_code == 405

        delete_response = await client.delete(
            f"/api/v1/receiving-weight-records/{record_id}"
        )
        assert delete_response.status_code == 405
