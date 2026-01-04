from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    InventoryLot,
    LpnContainer,
    LotLpnMembership,
    WarehouseLocation,
)
from app.repositories.custody_repo import add_custody_event


async def create_location(
    session: AsyncSession,
    site_code: str,
    location_code: str,
    location_name: str,
    location_type: str,
    created_by: Optional[str],
) -> WarehouseLocation:
    loc = WarehouseLocation(
        site_code=site_code,
        location_code=location_code,
        location_name=location_name,
        location_type=location_type,
        created_by=created_by,
    )
    session.add(loc)
    await session.flush()
    return loc


async def create_lpn(
    session: AsyncSession,
    lpn_code: str,
    container_type: str,
    initial_location_id: Optional[str],
    created_by: Optional[str],
) -> LpnContainer:
    lpn = LpnContainer(
        lpn_code=lpn_code,
        container_type=container_type,
        status="WIP",
        current_location_id=initial_location_id,
        created_by=created_by,
    )
    session.add(lpn)
    await session.flush()
    if initial_location_id:
        await add_custody_event(
            session=session,
            actor=created_by or "system",
            event_type="SCAN_IN",
            entity_type="LPN",
            entity_id=lpn.id,
            to_location_id=initial_location_id,
            metadata_json={"reason": "initial_create"},
        )
    return lpn


async def move_lpn(
    session: AsyncSession,
    lpn_id: str,
    to_location_id: Optional[str],
    actor: str,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
    to_location_code: Optional[str] = None,
) -> LpnContainer:
    lpn = await session.get(LpnContainer, lpn_id)
    if not lpn:
        raise ValueError("lpn_not_found")
    await add_custody_event(
        session=session,
        actor=actor,
        event_type="MOVE",
        entity_type="LPN",
        entity_id=lpn_id,
        from_location_id=lpn.current_location_id,
        to_location_id=to_location_id,
        to_location_code=to_location_code,
        reference=reference,
        notes=notes,
    )
    if to_location_id:
        lpn.current_location_id = to_location_id
    await session.flush()
    return lpn


async def create_lot(
    session: AsyncSession,
    lot_code: str,
    taxonomy_item_id: str,
    bol_id: Optional[str],
    created_by: Optional[str],
) -> InventoryLot:
    lot = InventoryLot(
        lot_code=lot_code,
        taxonomy_item_id=taxonomy_item_id,
        bol_id=bol_id,
        status="WIP",
        created_by=created_by,
    )
    session.add(lot)
    await session.flush()
    return lot


async def add_lpn_to_lot(session: AsyncSession, lot_id: str, lpn_id: str, added_by: Optional[str]) -> LotLpnMembership:
    membership = LotLpnMembership(
        lot_id=lot_id,
        lpn_id=lpn_id,
        added_by=added_by,
    )
    session.add(membership)
    await session.flush()
    return membership


async def remove_lpn_from_lot(
    session: AsyncSession,
    lot_id: str,
    lpn_id: str,
    removed_by: Optional[str],
    reason: Optional[str],
) -> LotLpnMembership:
    result = await session.execute(
        select(LotLpnMembership)
        .where(LotLpnMembership.lot_id == lot_id, LotLpnMembership.lpn_id == lpn_id, LotLpnMembership.removed_at.is_(None))
        .order_by(LotLpnMembership.added_at.desc())
        .limit(1)
    )
    membership = result.scalars().first()
    if not membership:
        raise ValueError("membership_not_found")
    membership.removed_at = func.now()
    membership.removed_by = removed_by
    membership.remove_reason = reason
    await session.flush()
    return membership


async def set_lpn_status(session: AsyncSession, lpn_id: str, status: str, actor: str, reason: Optional[str] = None) -> LpnContainer:
    lpn = await session.get(LpnContainer, lpn_id)
    if not lpn:
        raise ValueError("lpn_not_found")
    lpn.status = status
    await add_custody_event(
        session=session,
        actor=actor,
        event_type="ADJUSTMENT",
        entity_type="LPN",
        entity_id=lpn_id,
        metadata_json={"status_change": status, "reason": reason},
    )
    await session.flush()
    return lpn
