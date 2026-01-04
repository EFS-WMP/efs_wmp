from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bol import BOL
from app.models.domain_events import DomainEvent
from app.models.processing import (
    BatteryProcessingLine,
    BatteryProcessingSession,
    EwasteProcessingLine,
    EwasteProcessingSession,
)
from app.models.taxonomy import TaxonomyItem
from app.schemas.processing import (
    BatteryProcessingLineResponse,
    BatteryProcessingSessionCreate,
    BatteryProcessingSessionResponse,
    EwasteProcessingLineResponse,
    EwasteProcessingSessionCreate,
    EwasteProcessingSessionResponse,
)


async def _assert_bol_exists(db: AsyncSession, bol_id: str) -> None:
    bol = await db.get(BOL, bol_id)
    if not bol:
        raise ValueError("BOL not found")


async def _assert_taxonomy_item_exists(db: AsyncSession, taxonomy_item_id: str) -> None:
    item = await db.get(TaxonomyItem, taxonomy_item_id)
    if not item:
        raise ValueError(f"taxonomy_item_id not found: {taxonomy_item_id}")


def _compute_productivity_lbs_per_hour(
    total_weight: float,
    started_at,
    ended_at,
    headcount: int,
) -> Optional[float]:
    if not started_at or not ended_at or headcount <= 0:
        return None
    duration = ended_at - started_at
    if duration <= timedelta(0):
        return None
    hours = duration.total_seconds() / 3600
    if hours <= 0:
        return None
    return total_weight / (hours * headcount)


async def create_battery_processing_session(
    db: AsyncSession,
    data: BatteryProcessingSessionCreate,
    actor: str,
    request_id: str,
    correlation_id: str,
) -> BatteryProcessingSessionResponse:
    await _assert_bol_exists(db, data.bol_id)
    for line in data.lines:
        await _assert_taxonomy_item_exists(db, line.taxonomy_item_id)
        if line.contamination_taxonomy_item_id:
            await _assert_taxonomy_item_exists(db, line.contamination_taxonomy_item_id)

    session = BatteryProcessingSession(
        bol_id=data.bol_id,
        started_at=data.started_at,
        ended_at=data.ended_at,
        headcount=data.headcount,
        notes=data.notes,
    )
    db.add(session)
    await db.flush()

    lines = []
    for line in data.lines:
        line_row = BatteryProcessingLine(
            session_id=session.id,
            taxonomy_item_id=line.taxonomy_item_id,
            weight_lbs=line.weight_lbs,
            quantity=line.quantity,
            contamination_flag=line.contamination_flag,
            contamination_taxonomy_item_id=line.contamination_taxonomy_item_id,
            notes=line.notes,
        )
        db.add(line_row)
        lines.append(line_row)

    await db.commit()
    await db.refresh(session)

    payload = {
        "bol_id": session.bol_id,
        "line_count": len(lines),
    }
    event = DomainEvent(
        actor=actor,
        entity_type="BATTERY_PROCESSING_SESSION",
        entity_id=session.id,
        event_type="BATTERY_PROCESSING_SESSION_CREATED",
        payload_json=payload,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return BatteryProcessingSessionResponse(
        id=session.id,
        bol_id=session.bol_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        headcount=session.headcount,
        notes=session.notes,
        lines=[
            BatteryProcessingLineResponse(
                id=line.id,
                taxonomy_item_id=line.taxonomy_item_id,
                weight_lbs=float(line.weight_lbs),
                quantity=line.quantity,
                contamination_flag=line.contamination_flag,
                contamination_taxonomy_item_id=line.contamination_taxonomy_item_id,
                notes=line.notes,
            )
            for line in lines
        ],
    )


async def get_battery_processing_session(
    db: AsyncSession,
    session_id: str,
) -> Optional[BatteryProcessingSessionResponse]:
    session = await db.get(BatteryProcessingSession, session_id)
    if not session:
        return None
    result = await db.execute(
        select(BatteryProcessingLine).where(BatteryProcessingLine.session_id == session_id)
    )
    lines = result.scalars().all()
    return BatteryProcessingSessionResponse(
        id=session.id,
        bol_id=session.bol_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        headcount=session.headcount,
        notes=session.notes,
        lines=[
            BatteryProcessingLineResponse(
                id=line.id,
                taxonomy_item_id=line.taxonomy_item_id,
                weight_lbs=float(line.weight_lbs),
                quantity=line.quantity,
                contamination_flag=line.contamination_flag,
                contamination_taxonomy_item_id=line.contamination_taxonomy_item_id,
                notes=line.notes,
            )
            for line in lines
        ],
    )


async def create_ewaste_processing_session(
    db: AsyncSession,
    data: EwasteProcessingSessionCreate,
    actor: str,
    request_id: str,
    correlation_id: str,
) -> EwasteProcessingSessionResponse:
    await _assert_bol_exists(db, data.bol_id)
    for line in data.lines:
        await _assert_taxonomy_item_exists(db, line.taxonomy_item_id)

    session = EwasteProcessingSession(
        bol_id=data.bol_id,
        started_at=data.started_at,
        ended_at=data.ended_at,
        headcount=data.headcount,
        notes=data.notes,
    )
    db.add(session)
    await db.flush()

    lines = []
    for line in data.lines:
        line_row = EwasteProcessingLine(
            session_id=session.id,
            taxonomy_item_id=line.taxonomy_item_id,
            weight_lbs=line.weight_lbs,
            quantity=line.quantity,
            notes=line.notes,
        )
        db.add(line_row)
        lines.append(line_row)

    await db.commit()
    await db.refresh(session)

    payload = {
        "bol_id": session.bol_id,
        "line_count": len(lines),
    }
    event = DomainEvent(
        actor=actor,
        entity_type="EWASTE_PROCESSING_SESSION",
        entity_id=session.id,
        event_type="EWASTE_PROCESSING_SESSION_CREATED",
        payload_json=payload,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    total_weight = sum(float(line.weight_lbs) for line in lines)
    productivity = _compute_productivity_lbs_per_hour(
        total_weight, session.started_at, session.ended_at, session.headcount
    )

    return EwasteProcessingSessionResponse(
        id=session.id,
        bol_id=session.bol_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        headcount=session.headcount,
        notes=session.notes,
        lines=[
            EwasteProcessingLineResponse(
                id=line.id,
                taxonomy_item_id=line.taxonomy_item_id,
                weight_lbs=float(line.weight_lbs),
                quantity=line.quantity,
                notes=line.notes,
            )
            for line in lines
        ],
        productivity_lbs_per_hour=productivity,
    )


async def get_ewaste_processing_session(
    db: AsyncSession,
    session_id: str,
) -> Optional[EwasteProcessingSessionResponse]:
    session = await db.get(EwasteProcessingSession, session_id)
    if not session:
        return None
    result = await db.execute(
        select(EwasteProcessingLine).where(EwasteProcessingLine.session_id == session_id)
    )
    lines = result.scalars().all()
    total_weight = sum(float(line.weight_lbs) for line in lines)
    productivity = _compute_productivity_lbs_per_hour(
        total_weight, session.started_at, session.ended_at, session.headcount
    )
    return EwasteProcessingSessionResponse(
        id=session.id,
        bol_id=session.bol_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        headcount=session.headcount,
        notes=session.notes,
        lines=[
            EwasteProcessingLineResponse(
                id=line.id,
                taxonomy_item_id=line.taxonomy_item_id,
                weight_lbs=float(line.weight_lbs),
                quantity=line.quantity,
                notes=line.notes,
            )
            for line in lines
        ],
        productivity_lbs_per_hour=productivity,
    )
