import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bol import BOL, SourceType
from app.models.pickup_manifest import (
    PickupManifest,
    PickupManifestIntegrationAttempt,
    PickupManifestStateEvent,
)


def compute_manifest_fingerprint(odoo_stop_id: str, completion_timestamp_iso: str, driver_id: Optional[str], vehicle_id: Optional[str]) -> str:
    raw = "|".join([odoo_stop_id or "", completion_timestamp_iso or "", driver_id or "", vehicle_id or ""])
    return hashlib.sha256(raw.encode()).hexdigest()


def _next_manifest_number() -> str:
    return f"MAN-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"


async def _log_attempt(
    session: AsyncSession,
    outcome: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str],
    idempotency_key: Optional[str],
    manifest_fingerprint: Optional[str],
    pickup_manifest_id: Optional[str],
) -> None:
    attempt = PickupManifestIntegrationAttempt(
        pickup_manifest_id=pickup_manifest_id,
        source_system=payload.get("source_system", "ODOO"),
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        manifest_fingerprint=manifest_fingerprint,
        outcome=outcome,
        payload_json=payload or {},
    )
    session.add(attempt)
    await session.flush()


async def create_or_get_manifest_from_odoo(
    session: AsyncSession,
    payload: Dict[str, Any],
    correlation_id: Optional[str],
    idempotency_key: Optional[str],
    actor: Optional[str],
) -> PickupManifest:
    odoo_stop_id = payload.get("odoo_stop_id")
    completion_ts = payload.get("completion_timestamp") or payload.get("submitted_at")
    driver_id = payload.get("driver_id")
    vehicle_id = payload.get("vehicle_id")

    if not odoo_stop_id or not completion_ts:
        await _log_attempt(session, "REJECTED", payload, correlation_id, idempotency_key, None, None)
        raise ValueError("missing_required_fields")

    fingerprint = compute_manifest_fingerprint(odoo_stop_id, completion_ts, driver_id, vehicle_id)
    source_system = payload.get("source_system", "ODOO")

    result = await session.execute(
        select(PickupManifest).where(
            PickupManifest.source_system == source_system,
            PickupManifest.manifest_fingerprint == fingerprint,
        )
    )
    existing = result.scalars().first()
    if existing:
        await _log_attempt(session, "DUPLICATE_RETURNED", payload, correlation_id, idempotency_key, fingerprint, existing.id)
        return existing

    manifest_no = payload.get("manifest_no") or _next_manifest_number()
    status = payload.get("status") or "SUBMITTED"
    manifest = PickupManifest(
        manifest_no=manifest_no,
        status=status,
        source_system=source_system,
        odoo_day_route_id=payload.get("odoo_day_route_id"),
        odoo_stop_id=odoo_stop_id,
        odoo_pickup_occurrence_id=payload.get("odoo_pickup_occurrence_id"),
        odoo_work_order_id=payload.get("odoo_work_order_id"),
        customer_id=payload.get("customer_id"),
        service_location_id=payload.get("service_location_id"),
        route_snapshot_json=payload.get("route_snapshot_json") or {},
        pod_evidence_json=payload.get("pod_evidence_json") or {"items": []},
        manifest_fingerprint=fingerprint,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        submitted_at=datetime.fromisoformat(completion_ts) if completion_ts else None,
        submitted_by=actor,
        created_by=actor,
    )
    session.add(manifest)
    try:
        await session.flush()
        state_event = PickupManifestStateEvent(
            pickup_manifest_id=manifest.id,
            from_status=None,
            to_status=status,
            actor=actor,
            correlation_id=correlation_id,
            payload_json=payload or {},
        )
        session.add(state_event)
        await session.flush()
        await _log_attempt(session, "ACCEPTED", payload, correlation_id, idempotency_key, fingerprint, manifest.id)
        return manifest
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(PickupManifest).where(
                PickupManifest.source_system == source_system,
                PickupManifest.manifest_fingerprint == fingerprint,
            )
        )
        manifest = result.scalars().first()
        await _log_attempt(session, "DUPLICATE_RETURNED", payload, correlation_id, idempotency_key, fingerprint, manifest.id if manifest else None)
        if manifest:
            return manifest
        raise


async def transition_manifest_status(
    session: AsyncSession,
    manifest_id: str,
    to_status: str,
    actor: Optional[str],
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
    payload_json: Optional[Dict[str, Any]] = None,
) -> PickupManifest:
    manifest = await session.get(PickupManifest, manifest_id)
    if not manifest:
        raise ValueError("manifest_not_found")

    current = manifest.status
    if to_status == current:
        return manifest

    allowed = {
        "DRAFT": {"SUBMITTED", "VOIDED"},
        "SUBMITTED": {"BOUND_TO_BOL", "VOIDED"},
        "BOUND_TO_BOL": {"RECEIVED", "VOIDED"},
        "RECEIVED": {"CLOSED", "VOIDED"},
        "CLOSED": set(),
        "VOIDED": set(),
    }
    if to_status not in allowed.get(current, set()):
        raise ValueError("invalid_transition")
    if to_status == "VOIDED" and not reason:
        raise ValueError("void_reason_required")

    manifest.status = to_status
    manifest.updated_at = datetime.utcnow()
    if to_status == "VOIDED":
        manifest.voided_at = datetime.utcnow()
        manifest.voided_by = actor
        manifest.void_reason = reason

    event = PickupManifestStateEvent(
        pickup_manifest_id=manifest.id,
        from_status=current,
        to_status=to_status,
        actor=actor,
        reason=reason,
        correlation_id=correlation_id,
        payload_json=payload_json or {},
    )
    session.add(event)
    await session.flush()
    return manifest


async def bind_manifest_to_bol(
    session: AsyncSession,
    manifest_id: str,
    bol_id: str,
    actor: Optional[str],
    correlation_id: Optional[str] = None,
) -> PickupManifest:
    manifest = await session.get(PickupManifest, manifest_id)
    if not manifest:
        raise ValueError("manifest_not_found")

    bol = await session.get(BOL, bol_id)
    if not bol:
        raise ValueError("bol_not_found")
    if bol.source_type != SourceType.PICKUP.value:
        raise ValueError("bol_not_pickup")
    if manifest.status not in ("SUBMITTED", "BOUND_TO_BOL"):
        raise ValueError("manifest_not_ready_for_binding")
    if bol.pickup_manifest_id and bol.pickup_manifest_id != manifest_id:
        raise ValueError("bol_already_bound")

    bol.pickup_manifest_id = manifest_id
    if manifest.status != "BOUND_TO_BOL":
        await transition_manifest_status(
            session,
            manifest_id=manifest_id,
            to_status="BOUND_TO_BOL",
            actor=actor,
            correlation_id=correlation_id,
            payload_json={"binding_bol_id": bol_id},
        )
    await session.flush()
    return manifest


async def bol_binding_invariant_check(session: AsyncSession, bol_id: str) -> list[str]:
    violations: list[str] = []
    bol = await session.get(BOL, bol_id)
    if not bol:
        violations.append("bol_not_found")
        return violations
    if bol.source_type == SourceType.PICKUP.value and not bol.pickup_manifest_id:
        violations.append("pickup_manifest_missing_for_pickup_bol")
    if bol.pickup_manifest_id:
        manifest = await session.get(PickupManifest, bol.pickup_manifest_id)
        if manifest and manifest.status == "VOIDED":
            violations.append("pickup_manifest_voided")
    return violations
