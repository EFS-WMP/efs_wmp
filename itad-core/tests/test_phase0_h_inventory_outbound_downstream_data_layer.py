import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError

from sqlalchemy import text

from app.core.db import async_session, create_tables
from app.models.inventory import LotLpnMembership, InventoryLot, LpnContainer
from app.models.taxonomy import TaxonomyType, TaxonomyItem
from app.repositories import (
    add_lpn_to_lot,
    add_lpn_to_shipment,
    add_vendor_cert,
    confirm_disposition,
    create_disposition,
    create_location,
    create_lot,
    create_lpn,
    create_shipment,
    create_vendor,
    is_vendor_qualified,
    mark_shipment_status,
    move_lpn,
    remove_lpn_from_lot,
)
from app.repositories import artifacts_repo


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables():
    await create_tables()
    # Isolate each test run so unique constraints (location_code, lpn_code, shipment_no, vendor_code) do not collide
    async with async_session() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    artifact_link,
                    custody_event,
                    evidence_artifact,
                    lot_lpn_membership,
                    shipment_lpn,
                    disposition_record,
                    vendor_certification,
                    outbound_shipment,
                    inventory_lot,
                    lpn_container,
                    warehouse_location,
                    downstream_vendor
                RESTART IDENTITY CASCADE
                """
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_lpn_unique_and_custody_move_updates_location():
    async with async_session() as session:
        loc = await create_location(session, "MAIN", "DOCK", "Dock", "DOCK", "tester")
        lpn = await create_lpn(session, "LPN-0001", "PALLET", loc.id, "tester")
        lpn_id = lpn.id
        await session.commit()
        await session.refresh(lpn)
        assert lpn.current_location_id == loc.id

        # Unique constraint
        with pytest.raises(IntegrityError):
            await create_lpn(session, "LPN-0001", "PALLET", None, "tester")
            await session.commit()
        await session.rollback()

        loc2 = await create_location(session, "MAIN", "WIP_A1", "WIP A1", "STORAGE", "tester")
        await session.commit()
        await move_lpn(session, lpn_id, to_location_id=loc2.id, actor="mover")
        await session.commit()
        updated = await session.get(LpnContainer, lpn_id)
        assert updated.current_location_id == loc2.id


@pytest.mark.asyncio
async def test_lot_membership_append_only():
    async with async_session() as session:
        loc = await create_location(session, "MAIN", "DOCK", "Dock", "DOCK", "tester")
        lpn = await create_lpn(session, "LPN-0002", "PALLET", loc.id, "tester")
        ttype = TaxonomyType(
            group_code="INBOUND",
            type_code="EWASTE",
            type_name="Ewaste",
            effective_from=datetime.datetime.utcnow(),
            is_active=True,
        )
        session.add(ttype)
        await session.flush()
        titem = TaxonomyItem(
            taxonomy_type_id=ttype.id,
            variant_code="MIXED",
            variant_name="Mixed",
            sb20_flag=False,
            effective_from=datetime.datetime.utcnow(),
            is_active=True,
        )
        session.add(titem)
        await session.flush()
        lot = await create_lot(session, "LOT-0001", taxonomy_item_id=titem.id, bol_id=None, created_by="tester")
        await session.commit()

        membership = await add_lpn_to_lot(session, lot.id, lpn.id, added_by="tester")
        await session.commit()
        assert membership.removed_at is None

        await remove_lpn_from_lot(session, lot.id, lpn.id, removed_by="tester", reason="moved")
        await session.commit()
        await session.refresh(membership)
        assert membership.removed_at is not None


@pytest.mark.asyncio
async def test_quarantine_lpn_blocked_from_shipment_and_dispatch_sets_shipped():
    async with async_session() as session:
        loc = await create_location(session, "MAIN", "DOCK", "Dock", "DOCK", "tester")
        lpn = await create_lpn(session, "LPN-0003", "PALLET", loc.id, "tester")
        lpn.status = "QUARANTINE"
        await session.commit()

        shipment = await create_shipment(
            session,
            shipment_no="SHP-0001",
            origin_site_code="MAIN",
            carrier_name="Carrier",
            appointment_at=None,
            seal_number=None,
            hazmat_flag=False,
            destination_vendor_id=None,
            created_by="tester",
        )
        await session.commit()

        with pytest.raises(ValueError):
            await add_lpn_to_shipment(session, shipment.id, lpn.id, actor="loader")

        # reset status and add
        lpn.status = "READY"
        await session.commit()
        await add_lpn_to_shipment(session, shipment.id, lpn.id, actor="loader")
        await session.commit()

        await mark_shipment_status(session, shipment.id, "DISPATCHED", actor="dispatcher")
        await session.commit()
        await session.refresh(lpn)
        assert lpn.status == "SHIPPED"


@pytest.mark.asyncio
async def test_vendor_certification_and_disposition_confirmation_requires_proof():
    async with async_session() as session:
        vendor = await create_vendor(session, "VEND-001", "Vendor 1", allowlist_flag=True, created_by="tester")
        artifact = await artifacts_repo.create_artifact(
            session,
            artifact_type="CERT",
            sha256_hex="e" * 64,
            byte_size=10,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="cert-ref",
            visibility="INTERNAL",
            created_by="tester",
            metadata_json={},
        )
        await session.commit()

        await add_vendor_cert(
            session,
            vendor_id=vendor.id,
            cert_type="R2",
            effective_from=datetime.date.today(),
            expires_at=datetime.date.today() + datetime.timedelta(days=365),
            artifact_id=artifact.id,
            created_by="tester",
        )
        await session.commit()
        assert await is_vendor_qualified(session, vendor.id, cert_type="R2")

        ttype = TaxonomyType(
            group_code="INBOUND",
            type_code="EWASTE",
            type_name="Ewaste",
            effective_from=datetime.datetime.utcnow(),
            is_active=True,
        )
        session.add(ttype)
        await session.flush()
        titem = TaxonomyItem(
            taxonomy_type_id=ttype.id,
            variant_code="CRT",
            variant_name="CRT",
            sb20_flag=True,
            effective_from=datetime.datetime.utcnow(),
            is_active=True,
        )
        session.add(titem)
        await session.flush()
        lot = await create_lot(session, "LOT-0002", taxonomy_item_id=titem.id, bol_id=None, created_by="tester")
        await session.commit()
        disposition = await create_disposition(
            session, lot_id=lot.id, vendor_id=vendor.id, disposition_type="RECYCLE", shipment_id=None, decided_by="tester"
        )
        await session.commit()

        with pytest.raises(ValueError):
            await confirm_disposition(session, disposition.id, final_proof_artifact_id=None, actor="tester")
        with pytest.raises(ValueError):
            await confirm_disposition(session, disposition.id, final_proof_artifact_id=str(uuid.uuid4()), actor="tester")

        await confirm_disposition(session, disposition.id, final_proof_artifact_id=artifact.id, actor="tester")
        await session.commit()
        await session.refresh(disposition)
        assert disposition.status == "CONFIRMED"
