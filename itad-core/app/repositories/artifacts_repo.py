import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import ArtifactLink, EvidenceArtifact

ALLOWED_ENTITY_TYPES = {
    "BOL",
    "RECEIVING_RECORD",
    "BATTERY_SESSION",
    "EWASTE_SESSION",
    "ASSET",
    "LOT",
    "LPN",
    "SHIPMENT",
    "DISPOSITION",
    "SETTLEMENT",
}

SHA_REGEX = re.compile(r"^[0-9a-f]{64}$")


async def create_artifact(
    session: AsyncSession,
    artifact_type: str,
    sha256_hex: str,
    byte_size: int,
    mime_type: Optional[str],
    storage_provider: str,
    storage_ref: str,
    visibility: str,
    created_by: Optional[str],
    metadata_json: Optional[Dict[str, Any]],
    retention_until=None,
    storage_version: Optional[str] = None,
) -> EvidenceArtifact:
    if not SHA_REGEX.match(sha256_hex or ""):
        raise ValueError("invalid_sha256")
    artifact = EvidenceArtifact(
        artifact_type=artifact_type,
        sha256_hex=sha256_hex,
        byte_size=byte_size,
        mime_type=mime_type,
        storage_provider=storage_provider,
        storage_ref=storage_ref,
        storage_version=storage_version,
        retention_until=retention_until,
        visibility=visibility,
        created_by=created_by,
        metadata_json=metadata_json or {},
    )
    session.add(artifact)
    try:
        await session.flush()
        return artifact
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(EvidenceArtifact).where(
                EvidenceArtifact.sha256_hex == sha256_hex,
                EvidenceArtifact.storage_provider == storage_provider,
                EvidenceArtifact.storage_ref == storage_ref,
            )
        )
        existing = result.scalars().first()
        if existing:
            return existing
        raise


async def link_artifact(
    session: AsyncSession,
    artifact_id: str,
    entity_type: str,
    entity_id: str,
    link_role: str,
    created_by: Optional[str],
    notes: Optional[str] = None,
    visibility_override: Optional[str] = None,
) -> ArtifactLink:
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise ValueError("invalid_entity_type")
    link = ArtifactLink(
        artifact_id=artifact_id,
        entity_type=entity_type,
        entity_id=entity_id,
        link_role=link_role,
        created_by=created_by,
        notes=notes,
        visibility_override=visibility_override,
    )
    session.add(link)
    await session.flush()
    return link


def _is_visible(artifact_visibility: str, visibility_override: Optional[str], requester_role: Optional[str], include_hidden: bool) -> bool:
    effective_visibility = visibility_override or artifact_visibility
    if include_hidden:
        return True
    if effective_visibility == "COMPLIANCE_ONLY":
        return requester_role in ("compliance_admin", "compliance")
    if effective_visibility == "CUSTOMER":
        return requester_role in ("customer_export", "customer", "compliance_admin", "compliance", "internal")
    return True  # INTERNAL and default


async def list_artifacts_for_entity(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    include_hidden: bool = False,
    requester_role: Optional[str] = None,
) -> List[EvidenceArtifact]:
    result = await session.execute(
        select(EvidenceArtifact, ArtifactLink)
        .join(ArtifactLink, ArtifactLink.artifact_id == EvidenceArtifact.id)
        .where(ArtifactLink.entity_type == entity_type, ArtifactLink.entity_id == entity_id)
    )
    rows = result.all()
    visible = []
    for artifact, link in rows:
        if _is_visible(artifact.visibility, link.visibility_override, requester_role, include_hidden):
            visible.append(artifact)
    return visible
