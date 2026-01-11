from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.models.bol import BOL, SourceType
from app.models.domain_events import DomainEvent
from app.models.bol_stage_gates import BolStageGate, BolGateType
from app.models.workstreams import Workstream, WorkstreamType, WorkstreamStatus
from app.models.workstream_stage_gates import WorkstreamStageGate, WorkstreamGateType
from app.schemas.bol import BOLCreate, BOLResponse
from app.core.config import settings
from datetime import datetime
from typing import List, Dict, Any


# Transition matrices
BOL_TRANSITIONS = {
    None: ["REQUIREMENTS_CONFIRMED"],
    "REQUIREMENTS_CONFIRMED": ["PAPERWORK_VERIFIED"],
    "PAPERWORK_VERIFIED": ["STAGING_ZONE_ASSIGNED"],
    "STAGING_ZONE_ASSIGNED": ["RECEIVING_ANCHOR_RECORDED"],
    "RECEIVING_ANCHOR_RECORDED": ["WORKSTREAMS_OPENED"],
    "WORKSTREAMS_OPENED": ["BOL_CLOSED"],
}

WORKSTREAM_TRANSITIONS = {
    None: ["WORKSTREAM_OPENED"],
    "WORKSTREAM_OPENED": ["WORKSTREAM_STARTED"],
    "WORKSTREAM_STARTED": ["WORKSTREAM_COMPLETED", "WORKSTREAM_VOIDED"],
    "WORKSTREAM_COMPLETED": [],
    "WORKSTREAM_VOIDED": [],
}


async def validate_bol_transition(db: AsyncSession, bol_id: str, new_gate: BolGateType) -> bool:
    result = await db.execute(
        select(BolStageGate.gate_type).where(BolStageGate.bol_id == bol_id, BolStageGate.is_void == False).order_by(BolStageGate.occurred_at.desc())
    )
    last_gate = result.scalar()
    allowed = BOL_TRANSITIONS.get(last_gate.value if last_gate else None, [])
    return new_gate.value in allowed


async def validate_workstream_transition(db: AsyncSession, workstream_id: str, new_gate: WorkstreamGateType) -> bool:
    result = await db.execute(
        select(WorkstreamStageGate.gate_type).where(WorkstreamStageGate.workstream_id == workstream_id, WorkstreamStageGate.is_void == False).order_by(WorkstreamStageGate.occurred_at.desc())
    )
    last_gate = result.scalar()
    allowed = WORKSTREAM_TRANSITIONS.get(last_gate.value if last_gate else None, [])
    return new_gate.value in allowed


async def create_bol(db: AsyncSession, bol_data: BOLCreate, created_by: str, request_id: str, correlation_id: str) -> BOLResponse:
    bol_number = bol_data.bol_number
    if bol_number is None:
        # Auto-generate BOL number
        year = datetime.now().year
        result = await db.execute(text("SELECT nextval('bol_number_seq')"))
        seq = result.scalar()
        bol_number = f"BOL-{settings.site}-{year}-{seq:06d}"

    source_type_value = (
        bol_data.source_type.value if hasattr(bol_data.source_type, "value") else bol_data.source_type
    )
    if source_type_value == SourceType.PICKUP.value:
        raise ValueError("pickup_manifest_required_for_pickup")
    
    bol = BOL(
        bol_number=bol_number,
        source_type=bol_data.source_type,
        customer_snapshot_json=bol_data.customer_snapshot_json,
        requirement_profile_snapshot_json=bol_data.requirement_profile_snapshot_json,
        requirement_profile_version=bol_data.requirement_profile_version,
        requirement_profile_effective_from=bol_data.requirement_profile_effective_from,
        created_by=created_by,
    )
    db.add(bol)
    await db.commit()
    await db.refresh(bol)

    # Domain event
    source_type_value = bol.source_type.value if hasattr(bol.source_type, "value") else bol.source_type
    event = DomainEvent(
        entity_type="BOL",
        entity_id=bol.id,
        event_type="BOL_CREATED",
        payload_json={
            "bol_number": bol.bol_number,
            "source_type": source_type_value,
        },
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return BOLResponse(
        id=bol.id,
        bol_number=bol.bol_number,
        source_type=bol.source_type,
        customer_snapshot_json=bol.customer_snapshot_json,
        requirement_profile_snapshot_json=bol.requirement_profile_snapshot_json,
        requirement_profile_version=bol.requirement_profile_version,
        requirement_profile_effective_from=bol.requirement_profile_effective_from.isoformat() if bol.requirement_profile_effective_from else None,
        status=bol.status,
        created_at=bol.created_at.isoformat(),
        created_by=bol.created_by,
    )


async def append_bol_gate(db: AsyncSession, bol_id: str, gate_type: BolGateType, actor: str, payload: Dict[str, Any], request_id: str, correlation_id: str) -> BolStageGate:
    if not await validate_bol_transition(db, bol_id, gate_type):
        raise ValueError(f"Invalid transition to {gate_type}")
    
    gate = BolStageGate(
        bol_id=bol_id,
        gate_type=gate_type,
        actor=actor,
        payload_json=payload
    )
    db.add(gate)
    await db.commit()
    await db.refresh(gate)
    
    # Domain event
    event = DomainEvent(
        entity_type="BOL_STAGE_GATE",
        entity_id=gate.id,
        event_type="BOL_GATE_APPENDED",
        payload_json={"bol_id": bol_id, "gate_type": gate_type.value},
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()
    
    return gate


async def get_bol_state(db: AsyncSession, bol_id: str) -> Dict[str, Any]:
    # Get BOL
    bol_result = await db.execute(select(BOL).where(BOL.id == bol_id))
    bol = bol_result.scalar_one_or_none()
    if not bol:
        raise ValueError("BOL not found")
    
    # Get latest gate
    gate_result = await db.execute(
        select(BolStageGate).where(BolStageGate.bol_id == bol_id, BolStageGate.is_void == False).order_by(BolStageGate.occurred_at.desc())
    )
    latest_gate = gate_result.first()
    
    # Get workstreams
    workstreams_result = await db.execute(select(Workstream).where(Workstream.bol_id == bol_id))
    workstreams = workstreams_result.scalars().all()
    
    # Derive state
    derived_state = latest_gate.gate_type.value if latest_gate else "OPEN"
    disputed = any(gate.gate_type == BolGateType.BOL_CLOSED and gate.is_void for gate in await db.execute(select(BolStageGate).where(BolStageGate.bol_id == bol_id)))
    required_workstreams = []
    if bol.requires_battery_processing:
        required_workstreams.append("BATTERY")
    if bol.requires_ewaste_processing:
        required_workstreams.append("EWASTE")
    
    completed_workstreams = [ws.workstream_type.value for ws in workstreams if ws.status == WorkstreamStatus.COMPLETED]
    blockers = []
    if not any(gate.gate_type == BolGateType.RECEIVING_ANCHOR_RECORDED for gate in await db.execute(select(BolStageGate).where(BolStageGate.bol_id == bol_id, BolStageGate.is_void == False))):
        blockers.append("receiving_anchor_missing")
    if not bol.requirements_locked_at:
        blockers.append("requirements_not_confirmed")
    for req in required_workstreams:
        if req not in completed_workstreams:
            blockers.append(f"workstream_{req.lower()}_not_completed")
    
    return {
        "bol_id": bol_id,
        "derived_state": derived_state,
        "disputed": disputed,
        "requires_battery_processing": bol.requires_battery_processing,
        "requires_ewaste_processing": bol.requires_ewaste_processing,
        "closure_blockers": blockers
    }


async def confirm_requirements(db: AsyncSession, bol_id: str, requires_battery: bool, requires_ewaste: bool, rationale: str, actor: str, request_id: str, correlation_id: str):
    bol_result = await db.execute(select(BOL).where(BOL.id == bol_id))
    bol = bol_result.scalar_one_or_none()
    if not bol:
        raise ValueError("BOL not found")
    if bol.requirements_locked_at:
        raise ValueError("Requirements already locked")
    
    bol.requires_battery_processing = requires_battery
    bol.requires_ewaste_processing = requires_ewaste
    bol.requirements_locked_at = datetime.now()
    await db.commit()
    
    # Append gate
    await append_bol_gate(db, bol_id, BolGateType.REQUIREMENTS_CONFIRMED, actor, {"rationale": rationale}, request_id, correlation_id)


async def close_bol(db: AsyncSession, bol_id: str, actor: str, request_id: str, correlation_id: str):
    state = await get_bol_state(db, bol_id)
    if state["closure_blockers"]:
        raise ValueError(f"Cannot close BOL: {state['closure_blockers']}")
    
    await append_bol_gate(db, bol_id, BolGateType.BOL_CLOSED, actor, {}, request_id, correlation_id)


async def create_workstreams(db: AsyncSession, bol_id: str, actor: str, request_id: str, correlation_id: str) -> List[Workstream]:
    bol_result = await db.execute(select(BOL).where(BOL.id == bol_id))
    bol = bol_result.scalar_one_or_none()
    if not bol or not bol.requirements_locked_at:
        raise ValueError("BOL not found or requirements not confirmed")
    
    workstreams = []
    if bol.requires_battery_processing:
        ws = Workstream(bol_id=bol_id, workstream_type=WorkstreamType.BATTERY, actor=actor)
        workstreams.append(ws)
        db.add(ws)
    if bol.requires_ewaste_processing:
        ws = Workstream(bol_id=bol_id, workstream_type=WorkstreamType.EWASTE, actor=actor)
        workstreams.append(ws)
        db.add(ws)
    
    await db.commit()
    for ws in workstreams:
        await db.refresh(ws)
        # Append WORKSTREAM_OPENED gate
        gate = WorkstreamStageGate(workstream_id=ws.id, gate_type=WorkstreamGateType.WORKSTREAM_OPENED, actor=actor)
        db.add(gate)
    
    await db.commit()
    
    # Append BOL WORKSTREAMS_OPENED gate
    await append_bol_gate(db, bol_id, BolGateType.WORKSTREAMS_OPENED, actor, {"workstream_ids": [ws.id for ws in workstreams]}, request_id, correlation_id)
    
    return workstreams


async def append_workstream_gate(db: AsyncSession, workstream_id: str, gate_type: WorkstreamGateType, actor: str, payload: Dict[str, Any], request_id: str, correlation_id: str) -> WorkstreamStageGate:
    if not await validate_workstream_transition(db, workstream_id, gate_type):
        raise ValueError(f"Invalid transition to {gate_type}")
    
    gate = WorkstreamStageGate(
        workstream_id=workstream_id,
        gate_type=gate_type,
        actor=actor,
        payload_json=payload
    )
    db.add(gate)
    
    # Update workstream status if COMPLETED
    if gate_type == WorkstreamGateType.WORKSTREAM_COMPLETED:
        ws_result = await db.execute(select(Workstream).where(Workstream.id == workstream_id))
        ws = ws_result.scalar_one()
        ws.status = WorkstreamStatus.COMPLETED
        ws.closed_at = datetime.now()
    
    await db.commit()
    await db.refresh(gate)
    
    return gate
