from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.receiving import ReceivingWeightRecordV3
from app.models.receiving_record_voids import ReceivingRecordVoid
from app.models.domain_events import DomainEvent
from app.schemas.receiving import ReceivingWeightRecordV3Create, ReceivingWeightRecordV3Response, ReceivingRecordVoidCreate, ReceivingRecordVoidResponse
from typing import Optional
import uuid

ALLOWED_TARE_SOURCES = {
    "MEASURED_ON_SCALE",
    "CONTAINER_INSTANCE_SNAPSHOT",
    "CONTAINER_TYPE_PROFILE_SNAPSHOT",
    "MANUAL_TARE_WITH_APPROVAL",
}
NET_WEIGHT_TOLERANCE = 0.0001


async def validate_tare_policy(record_data: ReceivingWeightRecordV3Create) -> None:
    """Validate tare source policy and snapshots."""
    if record_data.tare_source not in ALLOWED_TARE_SOURCES:
        raise ValueError(f"tare_source must be one of {sorted(ALLOWED_TARE_SOURCES)}")
    if record_data.tare_source == "CONTAINER_TYPE_PROFILE_SNAPSHOT" and not record_data.tare_profile_snapshot_json:
        raise ValueError("tare_profile_snapshot_json required when tare_source is CONTAINER_TYPE_PROFILE_SNAPSHOT")
    if record_data.tare_source == "CONTAINER_INSTANCE_SNAPSHOT" and not record_data.tare_instance_snapshot_json:
        raise ValueError("tare_instance_snapshot_json required when tare_source is CONTAINER_INSTANCE_SNAPSHOT")


async def validate_net_weight(record_data: ReceivingWeightRecordV3Create) -> None:
    """Validate net weight calculation."""
    calculated_net = record_data.gross_weight - record_data.tare_weight
    if abs(calculated_net - record_data.net_weight) > NET_WEIGHT_TOLERANCE:
        raise ValueError(f"Net weight mismatch: calculated {calculated_net}, provided {record_data.net_weight}")


async def _get_void_entry(db: AsyncSession, receiving_record_id: str) -> Optional[ReceivingRecordVoid]:
    result = await db.execute(
        select(ReceivingRecordVoid)
        .where(ReceivingRecordVoid.receiving_record_id == receiving_record_id)
        .order_by(ReceivingRecordVoid.voided_at.desc())
    )
    return result.scalars().first()


async def create_receiving_weight_record(db: AsyncSession, record_data: ReceivingWeightRecordV3Create, created_by: str, request_id: str, correlation_id: str) -> ReceivingWeightRecordV3Response:
    # Validate tare policy
    await validate_tare_policy(record_data)

    # Validate net weight
    await validate_net_weight(record_data)

    record = ReceivingWeightRecordV3(
        bol_id=record_data.bol_id,
        occurred_at=record_data.occurred_at,
        container_type=record_data.container_type,
        quantity=record_data.quantity,
        gross_weight=record_data.gross_weight,
        tare_weight=record_data.tare_weight,
        net_weight=record_data.net_weight,
        scale_id=record_data.scale_id,
        hazard_class=record_data.hazard_class,
        un_number=record_data.un_number,
        ddr_status=record_data.ddr_status,
        receiver_name=record_data.receiver_name,
        receiver_employee_id=record_data.receiver_employee_id,
        receiver_signature_ref=record_data.receiver_signature_ref,
        notes=record_data.notes,
        material_received_as=record_data.material_received_as,
        weight_unit=record_data.weight_unit,
        receiver_signature_json=record_data.receiver_signature_json,
        tare_source=record_data.tare_source,
        tare_profile_snapshot_json=record_data.tare_profile_snapshot_json,
        tare_instance_snapshot_json=record_data.tare_instance_snapshot_json,
        declared_gross_weight=record_data.declared_gross_weight,
        declared_tare_weight=record_data.declared_tare_weight,
        declared_net_weight=record_data.declared_net_weight,
        declared_weight_source=record_data.declared_weight_source,
        reissue_of_id=record_data.reissue_of_id,
        created_by=created_by,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Domain event
    event = DomainEvent(
        entity_type="ReceivingWeightRecordV3",
        entity_id=record.id,
        event_type="RECEIVING_WEIGHT_RECORDED",
        payload_json={
            "bol_id": record.bol_id,
            "net_weight": str(record.net_weight),
            "material_received_as": record.material_received_as,
        },
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return ReceivingWeightRecordV3Response(
        id=record.id,
        bol_id=record.bol_id,
        occurred_at=record.occurred_at,
        container_type=record.container_type,
        quantity=record.quantity,
        gross_weight=record.gross_weight,
        tare_weight=record.tare_weight,
        net_weight=record.net_weight,
        scale_id=record.scale_id,
        hazard_class=record.hazard_class,
        un_number=record.un_number,
        ddr_status=record.ddr_status,
        receiver_name=record.receiver_name,
        receiver_employee_id=record.receiver_employee_id,
        receiver_signature_ref=record.receiver_signature_ref,
        notes=record.notes,
        is_void=False,
        void_reason=None,
        voided_record_id=None,
        created_at=record.created_at.isoformat(),
        created_by=record.created_by,
        material_received_as=record.material_received_as,
        weight_unit=record.weight_unit,
        receiver_signature_json=record.receiver_signature_json,
        tare_source=record.tare_source,
        tare_profile_snapshot_json=record.tare_profile_snapshot_json,
        tare_instance_snapshot_json=record.tare_instance_snapshot_json,
        declared_gross_weight=record.declared_gross_weight,
        declared_tare_weight=record.declared_tare_weight,
        declared_net_weight=record.declared_net_weight,
        declared_weight_source=record.declared_weight_source,
        reissue_of_id=record.reissue_of_id,
    )


async def void_receiving_record(db: AsyncSession, void_data: ReceivingRecordVoidCreate, request_id: str, correlation_id: str) -> ReceivingRecordVoidResponse:
    # Check if record exists and is not already voided
    record = await db.get(ReceivingWeightRecordV3, void_data.receiving_record_id)
    if not record:
        raise ValueError("Receiving record not found")
    existing_void = await _get_void_entry(db, void_data.receiving_record_id)
    if existing_void:
        raise ValueError("Record is already voided")

    # Create void entry
    void_entry = ReceivingRecordVoid(
        id=str(uuid.uuid4()),
        receiving_record_id=void_data.receiving_record_id,
        void_reason=void_data.void_reason,
        voided_by=void_data.voided_by,
    )
    db.add(void_entry)
    await db.commit()
    await db.refresh(void_entry)

    # Domain event
    event = DomainEvent(
        entity_type="ReceivingRecordVoid",
        entity_id=void_entry.id,
        event_type="RECEIVING_RECORD_VOIDED",
        payload_json={
            "receiving_record_id": void_entry.receiving_record_id,
            "void_reason": void_entry.void_reason,
            "voided_by": void_entry.voided_by,
        },
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return ReceivingRecordVoidResponse(
        id=void_entry.id,
        receiving_record_id=void_entry.receiving_record_id,
        void_reason=void_entry.void_reason,
        voided_by=void_entry.voided_by,
        voided_at=void_entry.voided_at,
    )


async def reissue_receiving_record(db: AsyncSession, original_record_id: str, reissue_data: ReceivingWeightRecordV3Create, created_by: str, request_id: str, correlation_id: str) -> ReceivingWeightRecordV3Response:
    # Check if original record exists
    original_record = await db.get(ReceivingWeightRecordV3, original_record_id)
    if not original_record:
        raise ValueError("Original receiving record not found")
    existing_void = await _get_void_entry(db, original_record_id)
    if not existing_void:
        raise ValueError("Original receiving record must be voided before reissue")

    # Set reissue_of_id
    reissue_data.reissue_of_id = original_record_id

    # Create new record as reissue
    new_record = await create_receiving_weight_record(db, reissue_data, created_by, request_id, correlation_id)

    event = DomainEvent(
        entity_type="ReceivingWeightRecordV3",
        entity_id=new_record.id,
        event_type="RECEIVING_RECORD_REISSUED",
        payload_json={
            "original_record_id": original_record_id,
            "new_record_id": new_record.id,
        },
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return new_record


async def get_receiving_record(
    db: AsyncSession,
    record_id: str,
    blind_mode: bool = False,
    include_declared: bool = True,
) -> Optional[ReceivingWeightRecordV3Response]:
    record = await db.get(ReceivingWeightRecordV3, record_id)
    if not record:
        return None
    void_entry = await _get_void_entry(db, record_id)
    redact_declared = blind_mode and not include_declared

    response = ReceivingWeightRecordV3Response(
        id=record.id,
        bol_id=record.bol_id,
        occurred_at=record.occurred_at,
        container_type=record.container_type,
        quantity=record.quantity,
        gross_weight=record.gross_weight,
        tare_weight=record.tare_weight,
        net_weight=record.net_weight,
        scale_id=record.scale_id,
        hazard_class=record.hazard_class,
        un_number=record.un_number,
        ddr_status=record.ddr_status,
        receiver_name=record.receiver_name,
        receiver_employee_id=record.receiver_employee_id,
        receiver_signature_ref=record.receiver_signature_ref,
        notes=record.notes,
        is_void=bool(void_entry),
        void_reason=void_entry.void_reason if void_entry else None,
        voided_record_id=void_entry.id if void_entry else None,
        created_at=record.created_at.isoformat(),
        created_by=record.created_by,
        material_received_as=record.material_received_as,
        weight_unit=record.weight_unit,
        receiver_signature_json=record.receiver_signature_json,
        tare_source=record.tare_source,
        tare_profile_snapshot_json=record.tare_profile_snapshot_json,
        tare_instance_snapshot_json=record.tare_instance_snapshot_json,
        declared_gross_weight=None if redact_declared else record.declared_gross_weight,
        declared_tare_weight=None if redact_declared else record.declared_tare_weight,
        declared_net_weight=None if redact_declared else record.declared_net_weight,
        declared_weight_source=None if redact_declared else record.declared_weight_source,
        reissue_of_id=record.reissue_of_id,
    )

    return response
