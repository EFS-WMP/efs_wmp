import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bol import BOL, SourceType
from app.models.pickup_manifest import (
    PickupManifest,
    PickupManifestIntegrationAttempt,
    PickupManifestStateEvent,
)
from app.models.receiving import ReceivingWeightRecordV3
from app.repositories.geocode_repo import geocode_gate
from app.repositories.pickup_manifest_repo import bind_manifest_to_bol
from app.schemas.pickup_manifest import PickupManifestSubmitRequest


def _next_manifest_number() -> str:
    return f"MAN-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"


def _bol_number_for_manifest(manifest_id: str) -> str:
    return f"BOL-PICKUP-{manifest_id[:8].upper()}"


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _compute_geocode_gate(location_snapshot: dict[str, Any] | None) -> Optional[str]:
    if not location_snapshot:
        return None
    confidence = location_snapshot.get("geocode_confidence")
    if confidence is None:
        return None
    try:
        return geocode_gate(float(confidence))
    except (TypeError, ValueError):
        return None


def _payload_dict(payload: PickupManifestSubmitRequest) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def _validate_payload(payload: PickupManifestSubmitRequest) -> None:
    if not payload.source_system:
        raise ValueError("missing_source_system")
    if not payload.manifest_fingerprint:
        raise ValueError("missing_manifest_fingerprint")
    if not payload.completed_at:
        raise ValueError("missing_completed_at")
    if payload.odoo_refs is None:
        raise ValueError("missing_odoo_refs")


async def _log_attempt(
    session: AsyncSession,
    outcome: str,
    payload: dict[str, Any],
    correlation_id: Optional[str],
    idempotency_key: Optional[str],
    manifest_fingerprint: Optional[str],
    pickup_manifest_id: Optional[str],
    error_message: Optional[str] = None,
) -> None:
    attempt = PickupManifestIntegrationAttempt(
        pickup_manifest_id=pickup_manifest_id,
        source_system=payload.get("source_system", "ODOO"),
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        manifest_fingerprint=manifest_fingerprint,
        outcome=outcome,
        error_message=error_message,
        payload_json=payload or {},
    )
    session.add(attempt)
    await session.flush()


async def _get_manifest_by_fingerprint(
    session: AsyncSession,
    source_system: str,
    manifest_fingerprint: str,
) -> Optional[PickupManifest]:
    result = await session.execute(
        select(PickupManifest).where(
            PickupManifest.source_system == source_system,
            PickupManifest.manifest_fingerprint == manifest_fingerprint,
        )
    )
    return result.scalars().first()


async def _ensure_bol_binding(
    session: AsyncSession,
    manifest: PickupManifest,
    payload: dict[str, Any],
    actor: str,
    correlation_id: Optional[str],
) -> BOL:
    """Create or reuse BOL for manifest (1:1 binding) without status transition.
    
    Phase 1: Create BOL bound to manifest but do NOT transition manifest status.
    Status stays SUBMITTED throughout Phase 1.
    """
    result = await session.execute(
        select(BOL).where(BOL.pickup_manifest_id == manifest.id)
    )
    bol = result.scalars().first()
    if not bol:
        bol = BOL(
            bol_number=_bol_number_for_manifest(manifest.id),
            source_type=SourceType.PICKUP.value,
            pickup_manifest_id=manifest.id,
            customer_snapshot_json={
                "customer_id": (payload.get("odoo_refs") or {}).get("customer_id")
            },
        )
        session.add(bol)
        await session.flush()
    # Note: DO NOT call bind_manifest_to_bol here; it would transition status to BOUND_TO_BOL.
    # Phase 1 keeps manifest.status as SUBMITTED.
    return bol


async def submit_pickup_manifest(
    session: AsyncSession,
    payload: PickupManifestSubmitRequest,
    *,
    idempotency_key: str,
    actor: str,
    correlation_id: Optional[str],
) -> tuple[PickupManifest, BOL, str, Optional[str]]:
    payload_data = _payload_dict(payload)
    try:
        _validate_payload(payload)
        geocode = _compute_geocode_gate(payload.location_snapshot_json)

        existing = await _get_manifest_by_fingerprint(
            session, payload.source_system, payload.manifest_fingerprint
        )
        if existing:
            bol = await _ensure_bol_binding(
                session, existing, payload_data, actor, correlation_id
            )
            await _log_attempt(
                session,
                outcome="DUPLICATE_RETURNED",
                payload=payload_data,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                manifest_fingerprint=payload.manifest_fingerprint,
                pickup_manifest_id=existing.id,
            )
            await session.commit()
            return existing, bol, "DUPLICATE_RETURNED", geocode

        route_snapshot = dict(payload.route_snapshot_json or {})
        if payload.location_snapshot_json:
            location_snapshot = dict(payload.location_snapshot_json)
            if geocode:
                location_snapshot["geocode_gate"] = geocode
            route_snapshot["location_snapshot"] = location_snapshot

        manifest = PickupManifest(
            manifest_no=_next_manifest_number(),
            status="SUBMITTED",
            source_system=payload.source_system,
            odoo_day_route_id=(payload.odoo_refs or {}).get("odoo_day_route_id"),
            odoo_stop_id=(payload.odoo_refs or {}).get("odoo_stop_id"),
            odoo_pickup_occurrence_id=(payload.odoo_refs or {}).get("odoo_pickup_occurrence_id"),
            odoo_work_order_id=(payload.odoo_refs or {}).get("odoo_work_order_id"),
            customer_id=(payload.odoo_refs or {}).get("customer_id"),
            service_location_id=(payload.odoo_refs or {}).get("service_location_id"),
            route_snapshot_json=route_snapshot,
            pod_evidence_json={"items": payload.pod_evidence or []},
            manifest_fingerprint=payload.manifest_fingerprint,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            submitted_at=_parse_datetime(payload.completed_at),
            submitted_by=actor,
            created_by=actor,
        )
        session.add(manifest)
        await session.flush()

        state_event = PickupManifestStateEvent(
            pickup_manifest_id=manifest.id,
            from_status=None,
            to_status="SUBMITTED",
            actor=actor,
            correlation_id=correlation_id,
            payload_json=payload_data or {},
        )
        session.add(state_event)
        await session.flush()

        bol = await _ensure_bol_binding(
            session, manifest, payload_data, actor, correlation_id
        )

        await _log_attempt(
            session,
            outcome="ACCEPTED",
            payload=payload_data,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            manifest_fingerprint=payload.manifest_fingerprint,
            pickup_manifest_id=manifest.id,
        )
        await session.commit()
        return manifest, bol, "ACCEPTED", geocode
    except IntegrityError:
        await session.rollback()
        existing = await _get_manifest_by_fingerprint(
            session, payload.source_system, payload.manifest_fingerprint
        )
        if existing:
            bol = await _ensure_bol_binding(
                session, existing, payload_data, actor, correlation_id
            )
            await _log_attempt(
                session,
                outcome="DUPLICATE_RETURNED",
                payload=payload_data,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                manifest_fingerprint=payload.manifest_fingerprint,
                pickup_manifest_id=existing.id,
            )
            await session.commit()
            geocode = _compute_geocode_gate(payload.location_snapshot_json)
            return existing, bol, "DUPLICATE_RETURNED", geocode
        await _log_attempt(
            session,
            outcome="ERROR",
            payload=payload_data,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            manifest_fingerprint=payload.manifest_fingerprint,
            pickup_manifest_id=None,
            error_message="integrity_error",
        )
        await session.commit()
        raise
    except ValueError as exc:
        await session.rollback()
        await _log_attempt(
            session,
            outcome="REJECTED",
            payload=payload_data,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            manifest_fingerprint=payload.manifest_fingerprint,
            pickup_manifest_id=None,
            error_message=str(exc),
        )
        await session.commit()
        raise
    except Exception as exc:
        await session.rollback()
        await _log_attempt(
            session,
            outcome="ERROR",
            payload=payload_data,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            manifest_fingerprint=payload.manifest_fingerprint,
            pickup_manifest_id=None,
            error_message=str(exc),
        )
        await session.commit()
        raise


async def get_pickup_manifest_chain(
    session: AsyncSession,
    pickup_manifest_id: str,
) -> tuple[PickupManifest, Optional[str], Optional[str], Optional[str]]:
    manifest = await session.get(PickupManifest, pickup_manifest_id)
    if not manifest:
        raise ValueError("manifest_not_found")

    result = await session.execute(
        select(BOL).where(BOL.pickup_manifest_id == pickup_manifest_id)
    )
    bol = result.scalars().first()
    bol_id = bol.id if bol else None

    receiving_id = None
    if bol_id:
        receiving_result = await session.execute(
            select(ReceivingWeightRecordV3.id).where(
                ReceivingWeightRecordV3.bol_id == bol_id
            )
        )
        receiving_id = receiving_result.scalar()

    geocode = None
    location_snapshot = (manifest.route_snapshot_json or {}).get("location_snapshot")
    if isinstance(location_snapshot, dict):
        geocode = _compute_geocode_gate(location_snapshot)
        if not geocode:
            geocode = location_snapshot.get("geocode_gate")

    return manifest, bol_id, receiving_id, geocode
