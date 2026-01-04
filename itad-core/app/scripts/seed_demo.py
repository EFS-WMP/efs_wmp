import asyncio
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session
from app.models.bol import BOL, SourceType
from app.models.taxonomy import TaxonomyItem, TaxonomyType
from app.services.receiving_service import (
    create_receiving_weight_record,
    get_receiving_record,
    reissue_receiving_record,
    void_receiving_record,
)
from app.schemas.receiving import ReceivingRecordVoidCreate, ReceivingWeightRecordV3Create
from app.repositories import (
    add_approval_event,
    add_lpn_to_lot,
    add_lpn_to_shipment,
    add_vendor_cert,
    artifacts_repo,
    bol_close_blockers,
    compute_next_case_no,
    create_discrepancy_case,
    create_disposition,
    create_lot,
    create_lpn,
    create_location,
    create_reconciliation_run,
    create_shipment,
    create_vendor,
    discrepancy_blockers,
    mark_shipment_status,
    move_lpn,
)
from app.repositories import downstream_repo as disposition_repo


async def seed_demo():
    async with async_session() as session:
        # Create BOL
        bol = BOL(
            bol_number="BOL-DEMO-001",
            source_type=SourceType.PICKUP.value,
            customer_snapshot_json={"name": "Demo Customer", "id": "odoo-cust-demo"},
            created_by="seed",
        )
        session.add(bol)
        await session.commit()
        await session.refresh(bol)
        print(f"Created BOL: {bol.id}")

        # Create Receiving Record with new fields
        record_data = ReceivingWeightRecordV3Create(
            bol_id=bol.id,
            occurred_at=datetime.datetime.utcnow(),
            material_received_as="CHEMICAL_X",
            container_type="PALLET",
            quantity=1,
            gross_weight=100.0,
            tare_weight=10.0,
            net_weight=90.0,
            weight_unit="LBS",
            scale_id="SCALE-DEMO",
            un_number="UN1993",
            hazard_class="3",
            ddr_status=True,
            receiver_employee_id="emp-demo-001",
            receiver_name="Demo Receiver",
            receiver_signature_json={"typed_name": "Demo Receiver", "signed_at": str(datetime.datetime.utcnow())},
            tare_source="CONTAINER_TYPE_PROFILE_SNAPSHOT",
            tare_profile_snapshot_json={"profile_id": "profile-demo", "tare_weight": 10.0, "container_type": "PALLET"},
            declared_gross_weight=100.0,
            declared_tare_weight=10.0,
            declared_net_weight=90.0,
            declared_weight_source="SHIPPER_MANIFEST",
        )

        record = await create_receiving_weight_record(
            session, record_data, "seed", "seed-req-001", "seed-corr-001"
        )
        print(f"Created Receiving Record: {record.id}")

        # Create another record for void/reissue demo
        record2_data = ReceivingWeightRecordV3Create(
            bol_id=bol.id,
            occurred_at=datetime.datetime.utcnow(),
            material_received_as="CHEMICAL_Y",
            container_type="DRUM",
            quantity=2,
            gross_weight=200.0,
            tare_weight=20.0,
            net_weight=180.0,
            weight_unit="LBS",
            scale_id="SCALE-DEMO",
            hazard_class=None,
            ddr_status=False,
            receiver_employee_id="emp-demo-001",
            receiver_name="Demo Receiver",
            receiver_signature_json={"typed_name": "Demo Receiver", "signed_at": str(datetime.datetime.utcnow())},
            tare_source="CONTAINER_INSTANCE_SNAPSHOT",
            tare_instance_snapshot_json={"instance_id": "instance-demo", "tare_weight": 20.0, "container_type": "DRUM"},
            declared_gross_weight=200.0,
            declared_tare_weight=20.0,
            declared_net_weight=180.0,
            declared_weight_source="SCALE_READING",
        )

        record2 = await create_receiving_weight_record(
            session, record2_data, "seed", "seed-req-002", "seed-corr-002"
        )
        print(f"Created Second Receiving Record: {record2.id}")

        # Demonstrate blind receiving redaction (declared fields hidden)
        blind_view = await get_receiving_record(session, record.id, blind_mode=True, include_declared=False)
        print(f"Blind view declared_gross_weight: {blind_view.declared_gross_weight}")

        # Demonstrate admin include_declared behavior
        admin_view = await get_receiving_record(session, record.id, blind_mode=True, include_declared=True)
        print(f"Admin view declared_gross_weight: {admin_view.declared_gross_weight}")

        # Void the second record
        void_data = ReceivingRecordVoidCreate(
            receiving_record_id=record2.id,
            void_reason="Incorrect tare weight entered",
            voided_by="seed-admin",
        )

        void_result = await void_receiving_record(
            session, void_data, "seed-req-003", "seed-corr-003"
        )
        print(f"Voided Record: {void_result.id}")

        # Reissue the voided record with corrected data
        reissue_data = ReceivingWeightRecordV3Create(
            bol_id=bol.id,
            occurred_at=datetime.datetime.utcnow(),
            material_received_as="CHEMICAL_Y",
            container_type="DRUM",
            quantity=2,
            gross_weight=200.0,
            tare_weight=15.0,  # Corrected tare
            net_weight=185.0,  # Corrected net
            weight_unit="LBS",
            scale_id="SCALE-DEMO",
            hazard_class=None,
            ddr_status=True,
            receiver_employee_id="emp-demo-001",
            receiver_name="Demo Receiver",
            receiver_signature_json={"typed_name": "Demo Receiver", "signed_at": str(datetime.datetime.utcnow())},
            tare_source="CONTAINER_INSTANCE_SNAPSHOT",
            tare_instance_snapshot_json={"instance_id": "instance-demo-corrected", "tare_weight": 15.0, "container_type": "DRUM"},
            declared_gross_weight=200.0,
            declared_tare_weight=15.0,
            declared_net_weight=185.0,
            declared_weight_source="SCALE_READING_CORRECTED",
        )

        reissued_record = await reissue_receiving_record(
            session, record2.id, reissue_data, "seed", "seed-req-004", "seed-corr-004"
        )
        print(f"Reissued Record: {reissued_record.id} (reissue of {record2.id})")

        # Seed taxonomy types
        now = datetime.datetime.utcnow()
        battery_type = TaxonomyType(
            group_code="INBOUND",
            type_code="BATTERY",
            type_name="Battery",
            effective_from=now,
            is_active=True,
        )
        ewaste_type = TaxonomyType(
            group_code="INBOUND",
            type_code="EWASTE",
            type_name="E-waste",
            effective_from=now,
            is_active=True,
        )
        session.add_all([battery_type, ewaste_type])
        await session.commit()
        await session.refresh(battery_type)
        await session.refresh(ewaste_type)

        # Seed taxonomy items
        battery_items = [
            TaxonomyItem(
                taxonomy_type_id=battery_type.id,
                variant_code="LIION_MIXED",
                variant_name="Lithium Ion Mixed",
                sb20_flag=False,
                effective_from=now,
                is_active=True,
            ),
            TaxonomyItem(
                taxonomy_type_id=battery_type.id,
                variant_code="ALKALINE_MIXED",
                variant_name="Alkaline Mixed",
                sb20_flag=False,
                effective_from=now,
                is_active=True,
            ),
            TaxonomyItem(
                taxonomy_type_id=battery_type.id,
                variant_code="LEAD_ACID",
                variant_name="Lead Acid",
                sb20_flag=False,
                effective_from=now,
                is_active=True,
            ),
        ]
        ewaste_items = [
            TaxonomyItem(
                taxonomy_type_id=ewaste_type.id,
                variant_code="CRT_TV",
                variant_name="CRT TV",
                sb20_flag=True,
                effective_from=now,
                is_active=True,
            ),
            TaxonomyItem(
                taxonomy_type_id=ewaste_type.id,
                variant_code="LCD_MONITOR",
                variant_name="LCD Monitor",
                sb20_flag=True,
                effective_from=now,
                is_active=True,
            ),
            TaxonomyItem(
                taxonomy_type_id=ewaste_type.id,
                variant_code="MIXED_EWASTE",
                variant_name="Mixed E-waste",
                sb20_flag=False,
                effective_from=now,
                is_active=True,
            ),
        ]
        session.add_all(battery_items + ewaste_items)
        await session.commit()
        for item in battery_items + ewaste_items:
            await session.refresh(item)

        # Battery processing session with lines
        # (omitted for brevity; already in previous seed)

        # Reconciliation examples
        recon_ok = await create_reconciliation_run(
            session,
            bol_id=bol.id,
            receiving_total_net_lbs=300.0,
            processing_total_lbs=295.0,
            threshold_pct=0.05,
            threshold_lbs=10.0,
            computed_by="seed",
            snapshot_json={"note": "within threshold"},
        )
        await session.commit()
        print(f"Reconciliation within threshold run: {recon_ok.id}")

        recon_over = await create_reconciliation_run(
            session,
            bol_id=bol.id,
            receiving_total_net_lbs=300.0,
            processing_total_lbs=200.0,
            threshold_pct=0.05,
            threshold_lbs=10.0,
            computed_by="seed",
            snapshot_json={"note": "over threshold"},
        )
        await session.commit()
        print(f"Reconciliation over threshold run: {recon_over.id}")

        blockers_before = await bol_close_blockers(session, bol.id)
        print(f"Blockers before approval: {blockers_before}")

        await add_approval_event(
            session,
            reconciliation_run_id=recon_over.id,
            decision="APPROVE",
            approver="seed-approver",
            reason="tolerance accepted",
            payload_json={"note": "approved in seed"},
        )
        await session.commit()

        blockers_after = await bol_close_blockers(session, bol.id)
        print(f"Blockers after approval: {blockers_after}")

        # Discrepancy example
        discrepancy = await create_discrepancy_case(
            session,
            bol_id=bol.id,
            status="OPEN",
            discrepancy_type="WEIGHT_MISMATCH",
            created_by="seed",
            description="Seed discrepancy example",
            artifact_refs_json={"refs": ["seed-artifact-1"]},
        )
        await session.commit()
        print(f"Discrepancy created: {discrepancy.id}")

        discrepancy_blockers_list = await discrepancy_blockers(session, bol.id)
        print(f"Discrepancy blockers: {discrepancy_blockers_list}")

        # Inventory and outbound seed
        dock = await create_location(session, "MAIN", "DOCK", "Dock", "DOCK", "seed")
        wip = await create_location(session, "MAIN", "WIP_A1", "WIP A1", "STORAGE", "seed")
        outbound = await create_location(session, "MAIN", "OUTBOUND", "Outbound", "OUTBOUND", "seed")
        await session.commit()

        lpn = await create_lpn(session, "LPN-0001", "PALLET", dock.id, "seed")
        await session.commit()
        await move_lpn(session, lpn.id, to_location_id=wip.id, actor="seed")
        await session.commit()

        lot = await create_lot(session, "LOT-0001", taxonomy_item_id=ewaste_items[2].id, bol_id=bol.id, created_by="seed")
        await session.commit()
        await add_lpn_to_lot(session, lot.id, lpn.id, added_by="seed")
        await session.commit()

        # Vendor + cert + proof artifact
        cert_artifact = await artifacts_repo.create_artifact(
            session,
            artifact_type="CERT",
            sha256_hex="f" * 64,
            byte_size=1234,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="vendor-cert",
            visibility="COMPLIANCE_ONLY",
            created_by="seed",
            metadata_json={},
        )
        await session.commit()

        vendor = await create_vendor(session, "VEND-001", "Vendor 1", allowlist_flag=True, created_by="seed")
        await session.commit()
        await add_vendor_cert(
            session,
            vendor_id=vendor.id,
            cert_type="R2",
            effective_from=datetime.date.today(),
            expires_at=datetime.date.today() + datetime.timedelta(days=365),
            artifact_id=cert_artifact.id,
            created_by="seed",
        )
        await session.commit()

        shipment = await create_shipment(
            session,
            shipment_no="SHP-0001",
            origin_site_code="MAIN",
            carrier_name="Carrier",
            appointment_at=None,
            seal_number="SEAL-1",
            hazmat_flag=False,
            destination_vendor_id=vendor.id,
            created_by="seed",
        )
        await session.commit()
        await add_lpn_to_shipment(session, shipment.id, lpn.id, actor="seed")
        await session.commit()
        await mark_shipment_status(session, shipment.id, "DISPATCHED", actor="seed")
        await session.commit()

        final_proof = await artifacts_repo.create_artifact(
            session,
            artifact_type="FINAL_PROOF",
            sha256_hex="a" * 64,
            byte_size=2222,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="final-proof",
            visibility="COMPLIANCE_ONLY",
            created_by="seed",
            metadata_json={},
        )
        await session.commit()
        disposition = await create_disposition(
            session,
            lot_id=lot.id,
            vendor_id=vendor.id,
            disposition_type="RECYCLE",
            shipment_id=shipment.id,
            decided_by="seed",
        )
        await session.commit()
        await disposition_repo.confirm_disposition(
            session,
            disposition_id=disposition.id,
            final_proof_artifact_id=final_proof.id,
            actor="seed",
        )
        await session.commit()
        print(f"Disposition confirmed: {disposition.id} with proof {final_proof.id}")
        await session.refresh(disposition)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_demo())
