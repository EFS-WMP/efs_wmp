import datetime
from decimal import Decimal
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.db import async_session, create_tables
from app.models.bol import BOL, SourceType
from app.models.pricing import PricingExternalRef
from app.models.settlement import SettlementPricingSnapshot, SettlementAdjustmentEvent
from app.repositories import (
    upsert_pricing_external_ref,
    create_settlement,
    create_pricing_snapshot,
    add_adjustment_event,
    compute_settlement_total,
)


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables():
    await create_tables()
    async with async_session() as session:
        # keep tests isolated
        for table in [
            "settlement_adjustment_event",
            "settlement_pricing_snapshot",
            "settlement",
            "pricing_external_ref",
            "bol",
        ]:
            await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        await session.commit()


def _demo_bol():
    return BOL(
        bol_number=f"BOL-{uuid.uuid4().hex[:6]}",
        source_type=SourceType.DROP_OFF.value,
        customer_snapshot_json={},
        requirement_profile_snapshot_json={},
        requirement_profile_version="v1",
        requirement_profile_effective_from=datetime.datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_pricing_external_ref_effective_dating():
    async with async_session() as session:
        ref1 = await upsert_pricing_external_ref(
            session,
            ref_type="RATE_CARD",
            odoo_record_model="product.pricelist",
            odoo_record_id="odoo-1",
            ref_hash_sha256="a" * 64,
            effective_from=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            effective_to=None,
            actor="tester",
        )
        await session.commit()
        assert ref1.is_active is True

        ref2 = await upsert_pricing_external_ref(
            session,
            ref_type="RATE_CARD",
            odoo_record_model="product.pricelist",
            odoo_record_id="odoo-1",
            ref_hash_sha256="b" * 64,
            effective_from=datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc),
            effective_to=None,
            actor="tester",
        )
        await session.commit()
        await session.refresh(ref1)
        await session.refresh(ref2)
        assert ref1.is_active is False
        assert ref1.effective_to == datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc)
        assert ref2.is_active is True


@pytest.mark.asyncio
async def test_snapshot_append_only_and_hash_deterministic():
    async with async_session() as session:
        bol = _demo_bol()
        session.add(bol)
        await session.commit()

        settlement = await create_settlement(session, bol_id=bol.id, customer_id=None, created_by="tester")
        await session.commit()

        payload = {"rate_card": "rc1"}
        basis = {"bases": [{"basis_code": "WEIGHT_LBS", "qty": 100}]}
        lines = {"lines": [{"charge_type_code": "WEIGHT", "qty": 100, "unit_rate": 0.5, "amount": 50}]}

        snap1 = await create_pricing_snapshot(
            session,
            settlement.id,
            pricing_payload_json=payload,
            basis_of_charge_json=basis,
            computed_lines_json=lines,
            created_by="tester",
        )
        snap2 = await create_pricing_snapshot(
            session,
            settlement.id,
            pricing_payload_json=payload,
            basis_of_charge_json=basis,
            computed_lines_json=lines,
            created_by="tester",
        )
        await session.commit()
        assert snap1.snapshot_no == 1
        assert snap2.snapshot_no == 2
        assert snap1.snapshot_hash_sha256 == snap2.snapshot_hash_sha256


@pytest.mark.asyncio
async def test_adjustment_requires_reason_and_approver():
    async with async_session() as session:
        bol = _demo_bol()
        session.add(bol)
        await session.commit()
        settlement = await create_settlement(session, bol_id=bol.id, created_by="tester")

        with pytest.raises(ValueError):
            await add_adjustment_event(
                session,
                settlement_id=settlement.id,
                decision="CREDIT",
                amount=10,
                reason_code="MANUAL_OVERRIDE",
                reason_text="",
                approver="boss",
                actor="tester",
            )

        with pytest.raises(ValueError):
            await add_adjustment_event(
                session,
                settlement_id=settlement.id,
                decision="CREDIT",
                amount=10,
                reason_code="MANUAL_OVERRIDE",
                reason_text="Needed",
                approver="",
                actor="tester",
            )


@pytest.mark.asyncio
async def test_compute_settlement_total():
    async with async_session() as session:
        bol = _demo_bol()
        session.add(bol)
        await session.commit()
        settlement = await create_settlement(session, bol_id=bol.id, created_by="tester")

        lines = {"lines": [{"amount": 100}, {"amount": 50}]}
        await create_pricing_snapshot(
            session,
            settlement.id,
            pricing_payload_json={},
            basis_of_charge_json={},
            computed_lines_json=lines,
            created_by="tester",
        )
        await add_adjustment_event(
            session,
            settlement_id=settlement.id,
            decision="CREDIT",
            amount=10,
            reason_code="DISPUTE_RESOLUTION",
            reason_text="make-good",
            approver="mgr",
            actor="tester",
        )
        await add_adjustment_event(
            session,
            settlement_id=settlement.id,
            decision="DEBIT",
            amount=-5,
            reason_code="OTHER",
            reason_text="fee",
            approver="mgr",
            actor="tester",
        )
        await session.commit()

        totals = await compute_settlement_total(session, settlement.id)
        assert totals["snapshot_amount"] == Decimal("150")
        assert totals["adjustments_total"] == Decimal("5")
        assert totals["total"] == Decimal("155")
