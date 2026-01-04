import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.db import async_session, create_tables
from app.models.bol import BOL, SourceType
from app.models.pickup_manifest import (
    GeocodeCache,
    PickupManifest,
    PickupManifestIntegrationAttempt,
    PickupManifestStateEvent,
)
from app.repositories import (
    attach_geocode_snapshot_to_manifest,
    bind_manifest_to_bol,
    bol_binding_invariant_check,
    compute_manifest_fingerprint,
    create_or_get_manifest_from_odoo,
    geocode_gate,
    transition_manifest_status,
    upsert_geocode_result,
)


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables():
    await create_tables()
    async with async_session() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    pickup_manifest_state_event,
                    pickup_manifest_integration_attempt,
                    geocode_cache,
                    pickup_manifest,
                    bol
                RESTART IDENTITY CASCADE
                """
            )
        )
        await session.commit()


def _minimal_bol_pickup():
    return BOL(
        bol_number=f"BOL-{uuid.uuid4().hex[:6]}",
        source_type=SourceType.PICKUP.value,
        customer_snapshot_json={},
        requirement_profile_snapshot_json={},
        requirement_profile_version="v1",
        requirement_profile_effective_from=datetime.datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_manifest_fingerprint_deduplicates_and_attempt_logs():
    payload = {
        "odoo_stop_id": "stop-1",
        "completion_timestamp": datetime.datetime.utcnow().isoformat(),
        "driver_id": "driver-1",
        "vehicle_id": "truck-1",
    }
    async with async_session() as session:
        manifest1 = await create_or_get_manifest_from_odoo(session, payload, correlation_id="corr-1", idempotency_key="idem-1", actor="tester")
        manifest2 = await create_or_get_manifest_from_odoo(session, payload, correlation_id="corr-1", idempotency_key="idem-1", actor="tester")
        await session.commit()

        assert manifest1.id == manifest2.id

        attempts = await session.execute(select(PickupManifestIntegrationAttempt))
        outcomes = [a.outcome for a in attempts.scalars().all()]
        assert "ACCEPTED" in outcomes
        assert "DUPLICATE_RETURNED" in outcomes


@pytest.mark.asyncio
async def test_transition_matrix_and_void_reason_required():
    async with async_session() as session:
        payload = {
            "odoo_stop_id": "stop-2",
            "completion_timestamp": datetime.datetime.utcnow().isoformat(),
        }
        manifest = await create_or_get_manifest_from_odoo(session, payload, correlation_id=None, idempotency_key=None, actor="tester")
        await session.commit()

        with pytest.raises(ValueError):
            await transition_manifest_status(session, manifest.id, "RECEIVED", actor="tester")

        with pytest.raises(ValueError):
            await transition_manifest_status(session, manifest.id, "VOIDED", actor="tester")

        await transition_manifest_status(session, manifest.id, "BOUND_TO_BOL", actor="tester")
        await transition_manifest_status(session, manifest.id, "VOIDED", actor="tester", reason="cancelled")
        await session.commit()

        events = await session.execute(select(PickupManifestStateEvent).where(PickupManifestStateEvent.pickup_manifest_id == manifest.id))
        assert len(events.scalars().all()) >= 3


@pytest.mark.asyncio
async def test_binding_requires_pickup_bol_and_submitted_status():
    async with async_session() as session:
        payload = {
            "odoo_stop_id": "stop-3",
            "completion_timestamp": datetime.datetime.utcnow().isoformat(),
        }
        manifest = await create_or_get_manifest_from_odoo(session, payload, correlation_id=None, idempotency_key=None, actor="tester")

        non_pickup_bol = _minimal_bol_pickup()
        non_pickup_bol.source_type = SourceType.DROP_OFF.value
        session.add(non_pickup_bol)
        await session.commit()

        with pytest.raises(ValueError):
            await bind_manifest_to_bol(session, manifest.id, non_pickup_bol.id, actor="tester")

        pickup_bol = _minimal_bol_pickup()
        session.add(pickup_bol)
        await session.commit()

        bound_manifest = await bind_manifest_to_bol(session, manifest.id, pickup_bol.id, actor="tester")
        await session.commit()
        await session.refresh(pickup_bol)
        assert pickup_bol.pickup_manifest_id == bound_manifest.id
        assert bound_manifest.status == "BOUND_TO_BOL"

        violations = await bol_binding_invariant_check(session, pickup_bol.id)
        assert violations == []


@pytest.mark.asyncio
async def test_geocode_gate_and_versioning():
    assert geocode_gate(0.9) == "AUTO_ACCEPT"
    assert geocode_gate(0.7) == "NEEDS_REVIEW"
    assert geocode_gate(0.5) == "MANUAL_REQUIRED"

    async with async_session() as session:
        entry1 = await upsert_geocode_result(
            session,
            normalized_address="123 MAIN ST",
            lat=1.0,
            lng=2.0,
            provider="MAPBOX",
            confidence=0.9,
            result_json={"source": "v1"},
            actor="tester",
        )
        await session.commit()
        await session.refresh(entry1)
        assert entry1.is_active is True

        entry2 = await upsert_geocode_result(
            session,
            normalized_address="123 MAIN ST",
            lat=3.0,
            lng=4.0,
            provider="MAPBOX",
            confidence=0.8,
            result_json={"source": "v2"},
            actor="tester",
        )
        await session.commit()
        await session.refresh(entry2)
        assert entry2.is_active is True

        prev = await session.get(GeocodeCache, entry1.id)
        assert prev.is_active is False
        assert prev.effective_to is not None


@pytest.mark.asyncio
async def test_attach_geocode_snapshot_and_missing_cache():
    async with async_session() as session:
        payload = {
            "odoo_stop_id": "stop-4",
            "completion_timestamp": datetime.datetime.utcnow().isoformat(),
        }
        manifest = await create_or_get_manifest_from_odoo(session, payload, correlation_id=None, idempotency_key=None, actor="tester")
        await session.commit()

        # no cache -> missing gate
        await attach_geocode_snapshot_to_manifest(session, manifest.id, raw_address="456 Pine St", actor="tester")
        await session.commit()
        await session.refresh(manifest)
        assert manifest.route_snapshot_json["geocode"]["gate"] == "MANUAL_REQUIRED"

        # add cache then attach again
        await upsert_geocode_result(
            session,
            normalized_address="456 PINE ST",
            lat=9.0,
            lng=10.0,
            provider="MAPBOX",
            confidence=0.9,
            result_json={"source": "v3"},
            actor="tester",
        )
        await attach_geocode_snapshot_to_manifest(session, manifest.id, raw_address="456 Pine St", actor="tester")
        await session.commit()
        await session.refresh(manifest)
        assert manifest.route_snapshot_json["geocode"]["gate"] == "AUTO_ACCEPT"
