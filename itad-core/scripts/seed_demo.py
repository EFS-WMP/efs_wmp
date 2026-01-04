import asyncio
import datetime
from decimal import Decimal

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.inventory import WarehouseLocation, LpnContainer, InventoryLot
from app.models.bol import BOL, SourceType
from app.models.taxonomy import TaxonomyType, TaxonomyItem
from app.repositories import (
    add_lpn_to_lot,
    add_lpn_to_shipment,
    add_vendor_cert,
    attach_geocode_snapshot_to_manifest,
    bind_manifest_to_bol,
    confirm_disposition,
    create_disposition,
    create_location,
    create_or_get_manifest_from_odoo,
    create_lot,
    create_lpn,
    create_shipment,
    create_vendor,
    create_settlement,
    create_pricing_snapshot,
    add_adjustment_event,
    compute_settlement_total,
    upsert_pricing_external_ref,
    is_vendor_qualified,
    mark_shipment_status,
    move_lpn,
    upsert_geocode_result,
)
from app.repositories import artifacts_repo


async def seed_demo():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Clean up any prior demo data so this script is rerunnable
        await session.execute(
            text(
                """
                DELETE FROM lot_lpn_membership WHERE lpn_id IN (SELECT id FROM lpn_container WHERE lpn_code IN ('LPN-0001','LPN-0002'));
                DELETE FROM shipment_lpn WHERE lpn_id IN (SELECT id FROM lpn_container WHERE lpn_code IN ('LPN-0001','LPN-0002'));
                DELETE FROM disposition_record WHERE lot_id IN (SELECT id FROM inventory_lot WHERE lot_code = 'LOT-0001');
                DELETE FROM outbound_shipment WHERE shipment_no = 'SHP-0001';
                DELETE FROM inventory_lot WHERE lot_code = 'LOT-0001';
                DELETE FROM lpn_container WHERE lpn_code IN ('LPN-0001','LPN-0002');
                DELETE FROM warehouse_location WHERE site_code = 'MAIN' AND location_code IN ('DOCK','WIP_A1','QUARANTINE','OUTBOUND');
                DELETE FROM vendor_certification WHERE vendor_id IN (SELECT id FROM downstream_vendor WHERE vendor_code = 'VEND-001');
                DELETE FROM downstream_vendor WHERE vendor_code = 'VEND-001';
                DELETE FROM pickup_manifest_state_event WHERE pickup_manifest_id IN (SELECT id FROM pickup_manifest WHERE manifest_no = 'MAN-DEMO');
                DELETE FROM pickup_manifest_integration_attempt WHERE manifest_fingerprint IS NOT NULL;
                DELETE FROM pickup_manifest WHERE manifest_no = 'MAN-DEMO';
                DELETE FROM geocode_cache WHERE address_hash IS NOT NULL;
                DELETE FROM bol WHERE bol_number = 'BOL-DEMO-PICKUP';
                DELETE FROM settlement_adjustment_event;
                DELETE FROM settlement_pricing_snapshot;
                DELETE FROM settlement;
                DELETE FROM pricing_external_ref;
                """
            )
        )
        await session.commit()

        # Minimal taxonomy (INBOUND / EWASTE / MIXED_EWASTE)
        result = await session.execute(
            select(TaxonomyType).where(TaxonomyType.group_code == "INBOUND", TaxonomyType.type_code == "EWASTE")
        )
        ttype = result.scalars().first()
        if not ttype:
            ttype = TaxonomyType(
                group_code="INBOUND",
                type_code="EWASTE",
                type_name="Ewaste",
                effective_from=datetime.datetime.utcnow(),
                is_active=True,
            )
            session.add(ttype)
            await session.flush()

        result = await session.execute(
            select(TaxonomyItem).where(TaxonomyItem.taxonomy_type_id == ttype.id, TaxonomyItem.variant_code == "MIXED_EWASTE")
        )
        titem = result.scalars().first()
        if not titem:
            titem = TaxonomyItem(
                taxonomy_type_id=ttype.id,
                variant_code="MIXED_EWASTE",
                variant_name="Mixed Ewaste",
                sb20_flag=False,
                effective_from=datetime.datetime.utcnow(),
                is_active=True,
            )
            session.add(titem)
            await session.flush()

        # Locations
        dock = await create_location(session, "MAIN", "DOCK", "Dock", "DOCK", "seed_demo")
        wip = await create_location(session, "MAIN", "WIP_A1", "WIP A1", "STORAGE", "seed_demo")
        quarantine = await create_location(session, "MAIN", "QUARANTINE", "Quarantine", "QUARANTINE", "seed_demo")
        outbound = await create_location(session, "MAIN", "OUTBOUND", "Outbound", "OUTBOUND", "seed_demo")
        await session.commit()
        print(f"Locations: DOCK={dock.id}, WIP_A1={wip.id}, QUARANTINE={quarantine.id}, OUTBOUND={outbound.id}")

        # LPNs and move
        lpn1 = await create_lpn(session, "LPN-0001", "PALLET", dock.id, "seed_demo")
        lpn2 = await create_lpn(session, "LPN-0002", "PALLET", dock.id, "seed_demo")
        await session.commit()
        await move_lpn(session, lpn1.id, to_location_id=wip.id, actor="seed_demo")
        await session.commit()
        print(f"LPNs created: {lpn1.id}, {lpn2.id}; moved LPN-0001 to WIP_A1")

        # Lot and membership
        lot = await create_lot(session, "LOT-0001", taxonomy_item_id=titem.id, bol_id=None, created_by="seed_demo")
        await add_lpn_to_lot(session, lot.id, lpn1.id, added_by="seed_demo")
        await session.commit()
        print(f"Lot created: {lot.id} (taxonomy_item={titem.variant_code}), LPN-0001 added")

        # Vendor + certification with artifact proof
        vendor = await create_vendor(session, "VEND-001", "Demo Vendor", allowlist_flag=True, created_by="seed_demo")
        cert_artifact = await artifacts_repo.create_artifact(
            session=session,
            artifact_type="CERT",
            sha256_hex="c" * 64,
            byte_size=1234,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="demo-cert.pdf",
            visibility="INTERNAL",
            created_by="seed_demo",
            metadata_json={"title": "R2 Certificate"},
        )
        await session.commit()
        await add_vendor_cert(
            session,
            vendor_id=vendor.id,
            cert_type="R2",
            effective_from=datetime.date.today(),
            expires_at=datetime.date.today() + datetime.timedelta(days=365),
            artifact_id=cert_artifact.id,
            created_by="seed_demo",
        )
        await session.commit()
        qualified = await is_vendor_qualified(session, vendor.id, cert_type="R2")
        print(f"Vendor created: {vendor.id}, qualified={qualified}, cert_artifact={cert_artifact.id}")

        # Shipment and dispatch
        shipment = await create_shipment(
            session,
            shipment_no="SHP-0001",
            origin_site_code="MAIN",
            carrier_name="Carrier Demo",
            appointment_at=None,
            seal_number="SEAL-123",
            hazmat_flag=False,
            destination_vendor_id=vendor.id,
            created_by="seed_demo",
        )
        await session.commit()
        await add_lpn_to_shipment(session, shipment.id, lpn1.id, actor="seed_demo")
        await session.commit()
        await mark_shipment_status(session, shipment.id, "DISPATCHED", actor="seed_demo")
        await session.commit()
        print(f"Shipment created: {shipment.id} and dispatched with LPN-0001")

        # Disposition with proof artifact
        proof_artifact = await artifacts_repo.create_artifact(
            session=session,
            artifact_type="FINAL_PROOF",
            sha256_hex="d" * 64,
            byte_size=2048,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="final-proof.pdf",
            visibility="COMPLIANCE_ONLY",
            created_by="seed_demo",
            metadata_json={"note": "Final downstream proof"},
        )
        await session.commit()

        disposition = await create_disposition(
            session,
            lot_id=lot.id,
            vendor_id=vendor.id,
            disposition_type="RECYCLE",
            shipment_id=shipment.id,
            decided_by="seed_demo",
        )
        await confirm_disposition(session, disposition.id, final_proof_artifact_id=proof_artifact.id, actor="seed_demo")
        await session.commit()
        print(
            f"Disposition confirmed: {disposition.id} (lot {lot.lot_code}) -> vendor {vendor.vendor_code} with proof {proof_artifact.id}"
        )

        # Pickup manifest bridge (Phase 0.I)
        geocode_entry = await upsert_geocode_result(
            session,
            normalized_address="123 DEMO ST, DEMO CITY",
            lat=37.0,
            lng=-122.0,
            provider="MAPBOX",
            confidence=0.9,
            result_json={"source": "seed"},
            actor="seed_demo",
        )
        payload = {
            "manifest_no": "MAN-DEMO",
            "odoo_stop_id": "stop-demo-1",
            "completion_timestamp": datetime.datetime.utcnow().isoformat(),
            "driver_id": "driver-demo",
            "vehicle_id": "truck-demo",
            "route_snapshot_json": {"address": "123 Demo St, Demo City"},
            "pod_evidence_json": {"items": [{"type": "SIGNATURE", "actor": "customer", "timestamp": datetime.datetime.utcnow().isoformat()}]},
        }
        manifest = await create_or_get_manifest_from_odoo(session, payload, correlation_id="corr-demo", idempotency_key="idem-demo", actor="seed_demo")
        # duplicate call proves idempotency/fingerprint
        manifest_dup = await create_or_get_manifest_from_odoo(session, payload, correlation_id="corr-demo", idempotency_key="idem-demo", actor="seed_demo")
        await session.commit()
        print(f"Pickup manifest created: {manifest.id} (duplicate returned id={manifest_dup.id}) geocode entry={geocode_entry.id}")

        bol_pickup = BOL(
            bol_number="BOL-DEMO-PICKUP",
            source_type=SourceType.PICKUP.value,
            customer_snapshot_json={"name": "Demo Customer"},
            requirement_profile_snapshot_json={"rules": ["demo"]},
            requirement_profile_version="v1",
            requirement_profile_effective_from=datetime.datetime.utcnow(),
        )
        session.add(bol_pickup)
        await session.commit()
        await bind_manifest_to_bol(session, manifest.id, bol_pickup.id, actor="seed_demo")
        await attach_geocode_snapshot_to_manifest(session, manifest.id, raw_address="123 Demo St, Demo City", actor="seed_demo")
        await session.commit()
        print(f"BOL {bol_pickup.bol_number} bound to manifest {manifest.id} with geocode gate {manifest.route_snapshot_json.get('geocode', {}).get('gate')}")

        # Pricing / settlement snapshot placeholders (Phase 0.J)
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        rate_ref = await upsert_pricing_external_ref(
            session,
            ref_type="RATE_CARD",
            odoo_record_model="product.pricelist",
            odoo_record_id="odoo-rc-1",
            ref_hash_sha256="e" * 64,
            effective_from=now,
            effective_to=None,
            actor="seed_demo",
        )
        profile_ref = await upsert_pricing_external_ref(
            session,
            ref_type="CUSTOMER_PRICING_PROFILE",
            odoo_record_model="res.partner",
            odoo_record_id="odoo-cust-1",
            ref_hash_sha256="f" * 64,
            effective_from=now,
            effective_to=None,
            actor="seed_demo",
        )
        service_ref = await upsert_pricing_external_ref(
            session,
            ref_type="SERVICE_CATALOG",
            odoo_record_model="product.template",
            odoo_record_id="odoo-cat-1",
            ref_hash_sha256="g" * 64,
            effective_from=now,
            effective_to=None,
            actor="seed_demo",
        )
        settlement = await create_settlement(session, bol_id=bol_pickup.id, customer_id=None, created_by="seed_demo")
        snapshot = await create_pricing_snapshot(
            session,
            settlement.id,
            pricing_payload_json={"rate_card": "demo", "rules_version": "v1"},
            basis_of_charge_json={"bases": [{"basis_code": "WEIGHT_LBS", "qty": 1500, "source": "receiving_net"}]},
            computed_lines_json={"lines": [{"charge_type_code": "WEIGHT", "qty": 1500, "unit_rate": 0.1, "amount": 150}]},
            customer_pricing_profile_ref_id=profile_ref.id,
            service_catalog_ref_id=service_ref.id,
            rate_card_ref_id=rate_ref.id,
            tier_ruleset_ref_id=None,
            created_by="seed_demo",
        )
        await add_adjustment_event(
            session,
            settlement_id=settlement.id,
            decision="CREDIT",
            amount=Decimal("5"),
            reason_code="MANUAL_OVERRIDE",
            reason_text="demo adjustment",
            approver="finance_mgr",
            actor="seed_demo",
            related_snapshot_id=snapshot.id,
        )
        await session.commit()
        totals = await compute_settlement_total(session, settlement.id)
        print(f"Settlement seeded: settlement={settlement.id}, snapshot={snapshot.id}, totals={totals}")

    print("Seeding complete (inventory/outbound/downstream demo)")


if __name__ == "__main__":
    asyncio.run(seed_demo())
