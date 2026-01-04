from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import CustodyEvent


async def add_custody_event(
    session: AsyncSession,
    actor: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    from_location_id: Optional[str] = None,
    to_location_id: Optional[str] = None,
    from_location_code: Optional[str] = None,
    to_location_code: Optional[str] = None,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    supersedes_event_id: Optional[str] = None,
) -> CustodyEvent:
    event = CustodyEvent(
        actor=actor,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        from_location_code=from_location_code,
        to_location_code=to_location_code,
        reference=reference,
        notes=notes,
        metadata_json=metadata_json or {},
        supersedes_event_id=supersedes_event_id,
    )
    session.add(event)
    await session.flush()
    return event


async def get_custody_timeline(session: AsyncSession, entity_type: str, entity_id: str) -> List[CustodyEvent]:
    result = await session.execute(
        select(CustodyEvent)
        .where(CustodyEvent.entity_type == entity_type, CustodyEvent.entity_id == entity_id)
        .order_by(CustodyEvent.occurred_at.asc())
    )
    return result.scalars().all()


async def has_unresolved_compensation(session: AsyncSession, entity_type: str, entity_id: str) -> bool:
    # Placeholder: unresolved compensation detection can be added later; currently returns False.
    return False
