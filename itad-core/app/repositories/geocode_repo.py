import hashlib
import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pickup_manifest import GeocodeCache, PickupManifest


def normalize_address(raw_address: str) -> str:
    return " ".join(raw_address.strip().split()).upper()


def compute_address_hash(normalized_address: str) -> str:
    return hashlib.sha256(normalized_address.encode()).hexdigest()


def geocode_gate(confidence: float) -> str:
    if confidence >= 0.85:
        return "AUTO_ACCEPT"
    if confidence >= 0.60:
        return "NEEDS_REVIEW"
    return "MANUAL_REQUIRED"


async def upsert_geocode_result(
    session: AsyncSession,
    normalized_address: str,
    lat: float,
    lng: float,
    provider: str,
    confidence: float,
    result_json,
    actor: Optional[str],
) -> GeocodeCache:
    address_hash = compute_address_hash(normalized_address)
    # End-date current active entries
    active_result = await session.execute(
        select(GeocodeCache).where(GeocodeCache.address_hash == address_hash, GeocodeCache.is_active.is_(True))
    )
    for row in active_result.scalars().all():
        row.is_active = False
        row.effective_to = datetime.datetime.utcnow()
    entry = GeocodeCache(
        address_hash=address_hash,
        normalized_address=normalized_address,
        latitude=lat,
        longitude=lng,
        provider=provider,
        confidence=confidence,
        result_json=result_json or {},
        created_by=actor,
        is_active=True,
    )
    session.add(entry)
    await session.flush()
    return entry


async def attach_geocode_snapshot_to_manifest(session: AsyncSession, manifest_id: str, raw_address: str, actor: Optional[str]) -> PickupManifest:
    manifest = await session.get(PickupManifest, manifest_id)
    if not manifest:
        raise ValueError("manifest_not_found")
    normalized = normalize_address(raw_address)
    address_hash = compute_address_hash(normalized)
    result = await session.execute(
        select(GeocodeCache)
        .where(GeocodeCache.address_hash == address_hash)
        .order_by(GeocodeCache.effective_from.desc())
        .limit(1)
    )
    geocode = result.scalars().first()
    snapshot = dict(manifest.route_snapshot_json or {})
    snapshot["address"] = raw_address
    if geocode:
        snapshot["geocode"] = {
            "normalized_address": geocode.normalized_address,
            "latitude": float(geocode.latitude),
            "longitude": float(geocode.longitude),
            "provider": geocode.provider,
            "confidence": float(geocode.confidence),
            "gate": geocode_gate(float(geocode.confidence)),
        }
    else:
        snapshot["geocode"] = {
            "status": "MISSING",
            "gate": geocode_gate(0.0),
        }
    manifest.route_snapshot_json = snapshot
    await session.flush()
    return manifest
