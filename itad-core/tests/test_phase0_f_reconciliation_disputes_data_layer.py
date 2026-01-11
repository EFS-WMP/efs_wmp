import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import async_session, create_tables
from app.models.bol import BOL, SourceType
from app.models.reconciliation import DiscrepancyCase, ReconciliationRun
from app.repositories import discrepancy_repo, reconciliation_repo


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables():
    await create_tables()


async def _create_bol(session) -> str:
    bol = BOL(
        bol_number=f"TEST-BOL-{uuid.uuid4()}",
        source_type=SourceType.DROP_OFF.value,
        customer_snapshot_json={"name": "Test"},
        created_by="test",
    )
    session.add(bol)
    await session.commit()
    await session.refresh(bol)
    return bol.id


@pytest.mark.asyncio
async def test_reconciliation_run_append_only_and_unique():
    async with async_session() as session:
        bol_id = await _create_bol(session)

        run1 = await reconciliation_repo.create_reconciliation_run(
            session,
            bol_id=bol_id,
            receiving_total_net_lbs=100,
            processing_total_lbs=95,
            threshold_pct=0.1,
            threshold_lbs=None,
            computed_by="tester",
            snapshot_json={"receiving_ids": [], "processing_ids": []},
        )
        await session.commit()
        assert run1.run_no == 1

        run2 = await reconciliation_repo.create_reconciliation_run(
            session,
            bol_id=bol_id,
            receiving_total_net_lbs=100,
            processing_total_lbs=90,
            threshold_pct=0.05,
            threshold_lbs=None,
            computed_by="tester",
            snapshot_json={},
        )
        await session.commit()
        assert run2.run_no == 2

        # Attempt duplicate run_no should fail
        dup = ReconciliationRun(
            id=str(uuid.uuid4()),
            bol_id=bol_id,
            run_no=2,
            status="WITHIN_THRESHOLD",
            receiving_total_net_lbs=100,
            processing_total_lbs=100,
            variance_lbs=0,
            variance_pct=0,
            threshold_pct=0.1,
        )
        session.add(dup)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_variance_pct_handles_zero_division():
    async with async_session() as session:
        bol_id = await _create_bol(session)
        run = await reconciliation_repo.create_reconciliation_run(
            session,
            bol_id=bol_id,
            receiving_total_net_lbs=0,
            processing_total_lbs=0,
            threshold_pct=0.1,
            threshold_lbs=None,
            computed_by="tester",
            snapshot_json={},
        )
        await session.commit()
        assert float(run.variance_pct) == 0


@pytest.mark.asyncio
async def test_approval_required_and_blocker_logic():
    async with async_session() as session:
        bol_id = await _create_bol(session)
        # Over threshold triggers approval_required
        over_run = await reconciliation_repo.create_reconciliation_run(
            session,
            bol_id=bol_id,
            receiving_total_net_lbs=100,
            processing_total_lbs=50,
            threshold_pct=0.1,
            threshold_lbs=None,
            computed_by="tester",
            snapshot_json={},
        )
        await session.commit()
        assert over_run.approval_required is True

        blockers = await reconciliation_repo.bol_close_blockers(session, bol_id)
        assert any(b["code"] == "RECONCILIATION_OVER_THRESHOLD" for b in blockers)

        # Approval clears blocker
        await reconciliation_repo.add_approval_event(
            session,
            reconciliation_run_id=over_run.id,
            decision="APPROVE",
            approver="approver1",
            reason="within tolerance",
            payload_json={"note": "approved"},
        )
        await session.commit()

        blockers_after = await reconciliation_repo.bol_close_blockers(session, bol_id)
        assert not blockers_after


@pytest.mark.asyncio
async def test_discrepancy_blockers_and_resolution():
    async with async_session() as session:
        bol_id = await _create_bol(session)
        case = await discrepancy_repo.create_discrepancy_case(
            session,
            bol_id=bol_id,
            status="OPEN",
            discrepancy_type="WEIGHT_MISMATCH",
            created_by="tester",
            description="Net mismatch",
            artifact_refs_json={"refs": ["artifact-1"]},
        )
        await session.commit()
        assert case.case_no == 1

        blockers = await discrepancy_repo.discrepancy_blockers(session, bol_id)
        assert any(b["code"] == "DISPUTE_OPEN" for b in blockers)

        resolved = await discrepancy_repo.resolve_discrepancy_case(
            session,
            case_id=case.id,
            resolved_by="resolver",
            resolution_text="Adjusted weight accepted",
        )
        await session.commit()
        assert resolved.status == "RESOLVED"

        blockers_after = await discrepancy_repo.discrepancy_blockers(session, bol_id)
        assert not blockers_after


@pytest.mark.asyncio
async def test_approval_event_append_only_and_status_derivation():
    async with async_session() as session:
        bol_id = await _create_bol(session)
        run = await reconciliation_repo.create_reconciliation_run(
            session,
            bol_id=bol_id,
            receiving_total_net_lbs=100,
            processing_total_lbs=60,
            threshold_pct=0.1,
            threshold_lbs=None,
            computed_by="tester",
            snapshot_json={},
        )
        await session.commit()

        status_before = await reconciliation_repo.get_effective_reconciliation_status(session, bol_id)
        assert status_before["status"] == "BLOCKED"

        await reconciliation_repo.add_approval_event(
            session,
            reconciliation_run_id=run.id,
            decision="REJECT",
            approver="approver2",
            reason="variance too high",
            payload_json={},
        )
        await session.commit()

        status_after = await reconciliation_repo.get_effective_reconciliation_status(session, bol_id)
        assert status_after["status"] == "BLOCKED"
        assert status_after["approval_status"] == "REJECT"


@pytest.mark.asyncio
async def test_artifact_refs_placeholder_allowed():
    async with async_session() as session:
        bol_id = await _create_bol(session)
        await discrepancy_repo.create_discrepancy_case(
            session,
            bol_id=bol_id,
            status="IN_DISPUTE",
            discrepancy_type="HAZMAT_ISSUE",
            created_by="tester",
            description="Hazmat docs missing",
            artifact_refs_json={"refs": ["photo1", "note1"]},
        )
        await session.commit()
        result = await session.execute(select(DiscrepancyCase).where(DiscrepancyCase.bol_id == bol_id))
        case = result.scalars().first()
        assert case is not None
        assert case.artifact_refs_json["refs"] == ["photo1", "note1"]
