import datetime
import hashlib
import json
from decimal import Decimal
from typing import Optional, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settlement import Settlement, SettlementPricingSnapshot, SettlementAdjustmentEvent


def _canonical_json_hash(pricing_payload_json: dict, basis_of_charge_json: dict, computed_lines_json: dict) -> str:
    def _canonical(obj: dict) -> str:
        return json.dumps(obj or {}, sort_keys=True, separators=(",", ":"), default=str)

    combined = "|".join(
        [
            _canonical(pricing_payload_json),
            _canonical(basis_of_charge_json),
            _canonical(computed_lines_json),
        ]
    )
    return hashlib.sha256(combined.encode()).hexdigest()


async def create_settlement(session: AsyncSession, bol_id: str, customer_id: Optional[str] = None, created_by: Optional[str] = None) -> Settlement:
    settlement = Settlement(
        bol_id=bol_id,
        customer_id=customer_id,
        status="DRAFT",
        created_by=created_by,
        metadata_json={},
    )
    session.add(settlement)
    await session.flush()
    return settlement


async def next_snapshot_no(session: AsyncSession, settlement_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(SettlementPricingSnapshot.snapshot_no), 0)).where(
            SettlementPricingSnapshot.settlement_id == settlement_id
        )
    )
    current_max = result.scalar_one()
    return int(current_max) + 1


async def create_pricing_snapshot(
    session: AsyncSession,
    settlement_id: str,
    pricing_payload_json: dict,
    basis_of_charge_json: dict,
    computed_lines_json: dict,
    customer_pricing_profile_ref_id: Optional[str] = None,
    service_catalog_ref_id: Optional[str] = None,
    rate_card_ref_id: Optional[str] = None,
    tier_ruleset_ref_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> SettlementPricingSnapshot:
    snap_no = await next_snapshot_no(session, settlement_id)
    snapshot_hash = _canonical_json_hash(pricing_payload_json, basis_of_charge_json, computed_lines_json)
    snapshot = SettlementPricingSnapshot(
        settlement_id=settlement_id,
        snapshot_no=snap_no,
        created_by=created_by,
        customer_pricing_profile_ref_id=customer_pricing_profile_ref_id,
        service_catalog_ref_id=service_catalog_ref_id,
        rate_card_ref_id=rate_card_ref_id,
        tier_ruleset_ref_id=tier_ruleset_ref_id,
        pricing_payload_json=pricing_payload_json or {},
        basis_of_charge_json=basis_of_charge_json or {},
        computed_lines_json=computed_lines_json or {"lines": []},
        snapshot_hash_sha256=snapshot_hash,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def add_adjustment_event(
    session: AsyncSession,
    settlement_id: str,
    decision: str,
    amount,
    reason_code: str,
    reason_text: str,
    approver: str,
    actor: str,
    related_snapshot_id: Optional[str] = None,
    currency: str = "USD",
    payload_json: Optional[dict] = None,
) -> SettlementAdjustmentEvent:
    if not reason_text:
        raise ValueError("reason_text_required")
    if not approver:
        raise ValueError("approver_required")

    event = SettlementAdjustmentEvent(
        settlement_id=settlement_id,
        decision=decision,
        amount=amount,
        currency=currency,
        reason_code=reason_code,
        reason_text=reason_text,
        approver=approver,
        actor=actor,
        related_snapshot_id=related_snapshot_id,
        payload_json=payload_json or {},
    )
    session.add(event)
    await session.flush()
    return event


async def compute_settlement_total(session: AsyncSession, settlement_id: str) -> Dict[str, Decimal]:
    latest_snap = await session.execute(
        select(SettlementPricingSnapshot)
        .where(SettlementPricingSnapshot.settlement_id == settlement_id)
        .order_by(SettlementPricingSnapshot.snapshot_no.desc())
        .limit(1)
    )
    snapshot = latest_snap.scalars().first()
    snap_amount = Decimal("0")
    if snapshot:
        lines = (snapshot.computed_lines_json or {}).get("lines", [])
        for line in lines:
            amount = line.get("amount")
            if amount is not None:
                snap_amount += Decimal(str(amount))

    adjustments = await session.execute(
        select(SettlementAdjustmentEvent).where(SettlementAdjustmentEvent.settlement_id == settlement_id)
    )
    adj_total = Decimal("0")
    for adj in adjustments.scalars().all():
        adj_total += Decimal(str(adj.amount))

    total = snap_amount + adj_total
    return {"snapshot_amount": snap_amount, "adjustments_total": adj_total, "total": total}
