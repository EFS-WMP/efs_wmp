from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import LpnContainer, OutboundShipment, ShipmentLpn
from app.repositories.custody_repo import add_custody_event


async def create_shipment(
    session: AsyncSession,
    shipment_no: str,
    origin_site_code: str,
    carrier_name: Optional[str],
    appointment_at,
    seal_number: Optional[str],
    hazmat_flag: bool,
    destination_vendor_id: Optional[str],
    created_by: Optional[str],
) -> OutboundShipment:
    shipment = OutboundShipment(
        shipment_no=shipment_no,
        status="PLANNED",
        origin_site_code=origin_site_code,
        carrier_name=carrier_name,
        appointment_at=appointment_at,
        seal_number=seal_number,
        hazmat_flag=hazmat_flag,
        destination_vendor_id=destination_vendor_id,
        created_by=created_by,
    )
    session.add(shipment)
    await session.flush()
    return shipment


async def add_lpn_to_shipment(session: AsyncSession, shipment_id: str, lpn_id: str, actor: str) -> ShipmentLpn:
    lpn = await session.get(LpnContainer, lpn_id)
    if not lpn:
        raise ValueError("lpn_not_found")
    if lpn.status == "QUARANTINE":
        raise ValueError("lpn_quarantine_block")
    link = ShipmentLpn(
        shipment_id=shipment_id,
        lpn_id=lpn_id,
    )
    session.add(link)
    await session.flush()
    # Optionally set status to READY when loaded to shipment
    lpn.status = "READY"
    await session.flush()
    return link


async def mark_shipment_status(session: AsyncSession, shipment_id: str, new_status: str, actor: str) -> OutboundShipment:
    shipment = await session.get(OutboundShipment, shipment_id)
    if not shipment:
        raise ValueError("shipment_not_found")
    shipment.status = new_status
    if new_status == "DISPATCHED":
        result = await session.execute(select(ShipmentLpn).where(ShipmentLpn.shipment_id == shipment_id))
        links = result.scalars().all()
        for link in links:
            lpn = await session.get(LpnContainer, link.lpn_id)
            if lpn:
                lpn.status = "SHIPPED"
                await add_custody_event(
                    session=session,
                    actor=actor,
                    event_type="SHIP",
                    entity_type="LPN",
                    entity_id=lpn.id,
                    reference=shipment.shipment_no,
                )
    await session.flush()
    return shipment
