from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reconciliation import ReconciliationApprovalEvent, ReconciliationRun


async def compute_next_run_no(session: AsyncSession, bol_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(ReconciliationRun.run_no), 0)).where(ReconciliationRun.bol_id == bol_id)
    )
    return (result.scalar() or 0) + 1


async def create_reconciliation_run(
    session: AsyncSession,
    bol_id: str,
    receiving_total_net_lbs,
    processing_total_lbs,
    threshold_pct,
    threshold_lbs,
    computed_by: Optional[str],
    snapshot_json: Dict[str, Any],
) -> ReconciliationRun:
    run_no = await compute_next_run_no(session, bol_id)
    variance_lbs = (receiving_total_net_lbs or 0) - (processing_total_lbs or 0)
    variance_pct = 0 if (receiving_total_net_lbs or 0) == 0 else variance_lbs / receiving_total_net_lbs

    approval_required = False
    status = "WITHIN_THRESHOLD"

    if threshold_lbs is not None and abs(variance_lbs) > threshold_lbs:
        approval_required = True
    if threshold_pct is not None and abs(variance_pct) > threshold_pct:
        approval_required = True

    if approval_required:
        status = "OVER_THRESHOLD"

    reconciliation_run = ReconciliationRun(
        bol_id=bol_id,
        run_no=run_no,
        status=status,
        receiving_total_net_lbs=receiving_total_net_lbs,
        processing_total_lbs=processing_total_lbs,
        variance_lbs=variance_lbs,
        variance_pct=variance_pct,
        threshold_pct=threshold_pct,
        threshold_lbs=threshold_lbs,
        approval_required=approval_required,
        computed_by=computed_by,
        snapshot_json=snapshot_json or {},
    )
    session.add(reconciliation_run)
    await session.flush()
    return reconciliation_run


async def add_approval_event(
    session: AsyncSession,
    reconciliation_run_id: str,
    decision: str,
    approver: str,
    reason: str,
    payload_json: Optional[Dict[str, Any]] = None,
) -> ReconciliationApprovalEvent:
    event = ReconciliationApprovalEvent(
        reconciliation_run_id=reconciliation_run_id,
        decision=decision,
        approver=approver,
        reason=reason,
        payload_json=payload_json or {},
    )
    session.add(event)
    await session.flush()
    return event


async def _latest_run(session: AsyncSession, bol_id: str) -> Optional[ReconciliationRun]:
    result = await session.execute(
        select(ReconciliationRun)
        .where(ReconciliationRun.bol_id == bol_id)
        .order_by(ReconciliationRun.run_no.desc(), ReconciliationRun.computed_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _latest_approval(session: AsyncSession, reconciliation_run_id: str) -> Optional[ReconciliationApprovalEvent]:
    result = await session.execute(
        select(ReconciliationApprovalEvent)
        .where(ReconciliationApprovalEvent.reconciliation_run_id == reconciliation_run_id)
        .order_by(ReconciliationApprovalEvent.decided_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def get_effective_reconciliation_status(session: AsyncSession, bol_id: str) -> Dict[str, Any]:
    run = await _latest_run(session, bol_id)
    if not run:
        return {"status": "NONE", "approval_required": False}

    status = run.status
    approval_status = None

    if run.status == "WITHIN_THRESHOLD":
        status = "OK"
    elif run.status == "OVER_THRESHOLD":
        approval = await _latest_approval(session, run.id)
        if approval:
            approval_status = approval.decision
            if approval.decision == "APPROVE":
                status = "APPROVED"
            else:
                status = "BLOCKED"
        else:
            status = "BLOCKED"

    return {
        "status": status,
        "approval_required": run.approval_required,
        "run_id": run.id,
        "approval_status": approval_status,
        "variance_lbs": float(run.variance_lbs),
        "variance_pct": float(run.variance_pct),
        "threshold_pct": float(run.threshold_pct),
        "threshold_lbs": float(run.threshold_lbs) if run.threshold_lbs is not None else None,
    }


async def bol_close_blockers(session: AsyncSession, bol_id: str) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    effective_status = await get_effective_reconciliation_status(session, bol_id)
    if effective_status.get("status") == "BLOCKED":
        blockers.append(
            {
                "code": "RECONCILIATION_OVER_THRESHOLD",
                "details": {
                    "variance_lbs": effective_status.get("variance_lbs"),
                    "variance_pct": effective_status.get("variance_pct"),
                    "threshold_pct": effective_status.get("threshold_pct"),
                    "threshold_lbs": effective_status.get("threshold_lbs"),
                },
            }
        )
    return blockers
