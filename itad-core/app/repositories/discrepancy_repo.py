from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reconciliation import DiscrepancyCase


async def compute_next_case_no(session: AsyncSession, bol_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(DiscrepancyCase.case_no), 0)).where(DiscrepancyCase.bol_id == bol_id)
    )
    return (result.scalar() or 0) + 1


async def create_discrepancy_case(
    session: AsyncSession,
    bol_id: str,
    status: str,
    discrepancy_type: str,
    created_by: str,
    description: Optional[str],
    artifact_refs_json: Optional[Dict[str, Any]],
) -> DiscrepancyCase:
    case_no = await compute_next_case_no(session, bol_id)
    case = DiscrepancyCase(
        bol_id=bol_id,
        case_no=case_no,
        status=status,
        discrepancy_type=discrepancy_type,
        created_by=created_by,
        description=description,
        artifact_refs_json=artifact_refs_json,
    )
    session.add(case)
    await session.flush()
    return case


async def resolve_discrepancy_case(
    session: AsyncSession,
    case_id: str,
    resolved_by: str,
    resolution_text: str,
) -> DiscrepancyCase:
    case = await session.get(DiscrepancyCase, case_id)
    if not case:
        raise ValueError("case_not_found")
    if case.status not in ("OPEN", "IN_DISPUTE"):
        raise ValueError("case_not_resolvable")

    case.status = "RESOLVED"
    case.resolved_by = resolved_by
    case.resolution_text = resolution_text
    case.resolved_at = func.now()
    await session.flush()
    return case


async def list_open_cases(session: AsyncSession, bol_id: str) -> List[DiscrepancyCase]:
    result = await session.execute(
        select(DiscrepancyCase).where(
            DiscrepancyCase.bol_id == bol_id, DiscrepancyCase.status.in_(("OPEN", "IN_DISPUTE"))
        )
    )
    return result.scalars().all()


async def has_open_case(session: AsyncSession, bol_id: str) -> bool:
    result = await session.execute(
        select(func.count()).select_from(DiscrepancyCase).where(
            DiscrepancyCase.bol_id == bol_id, DiscrepancyCase.status.in_(("OPEN", "IN_DISPUTE"))
        )
    )
    return (result.scalar() or 0) > 0


async def discrepancy_blockers(session: AsyncSession, bol_id: str) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    open_cases = await list_open_cases(session, bol_id)
    if open_cases:
        blockers.append(
            {
                "code": "DISPUTE_OPEN",
                "details": {"open_case_ids": [case.id for case in open_cases]},
            }
        )
    return blockers
