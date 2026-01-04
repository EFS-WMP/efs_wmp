from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceArtifact
from app.models.inventory import DispositionRecord, DownstreamVendor, VendorCertification


async def create_vendor(
    session: AsyncSession,
    vendor_code: str,
    vendor_name: str,
    allowlist_flag: bool,
    created_by: Optional[str],
) -> DownstreamVendor:
    vendor = DownstreamVendor(
        vendor_code=vendor_code,
        vendor_name=vendor_name,
        allowlist_flag=allowlist_flag,
        created_by=created_by,
    )
    session.add(vendor)
    await session.flush()
    return vendor


async def add_vendor_cert(
    session: AsyncSession,
    vendor_id: str,
    cert_type: str,
    effective_from,
    expires_at,
    artifact_id: Optional[str],
    created_by: Optional[str],
    cert_number: Optional[str] = None,
) -> VendorCertification:
    cert = VendorCertification(
        vendor_id=vendor_id,
        cert_type=cert_type,
        cert_number=cert_number,
        issued_at=str(effective_from),
        expires_at=str(expires_at) if expires_at else None,
        effective_from=str(effective_from),
        effective_to=None,
        is_active=True,
        created_by=created_by,
        artifact_id=artifact_id,
    )
    session.add(cert)
    await session.flush()
    return cert


async def is_vendor_qualified(session: AsyncSession, vendor_id: str, cert_type: Optional[str] = None, at_date: Optional[date] = None) -> bool:
    at_date = at_date or date.today()
    vendor = await session.get(DownstreamVendor, vendor_id)
    if not vendor or not vendor.is_active or not vendor.allowlist_flag:
        return False
    query = select(VendorCertification).where(
        VendorCertification.vendor_id == vendor_id,
        VendorCertification.is_active.is_(True),
    )
    if cert_type:
        query = query.where(VendorCertification.cert_type == cert_type)
    result = await session.execute(query)
    certs = result.scalars().all()
    for cert in certs:
        if cert.expires_at:
            try:
                exp_date = date.fromisoformat(cert.expires_at)
                if exp_date < at_date:
                    continue
            except ValueError:
                continue
        return True
    return False


async def create_disposition(
    session: AsyncSession,
    lot_id: str,
    vendor_id: str,
    disposition_type: str,
    shipment_id: Optional[str],
    decided_by: Optional[str],
) -> DispositionRecord:
    disposition = DispositionRecord(
        lot_id=lot_id,
        vendor_id=vendor_id,
        shipment_id=shipment_id,
        disposition_type=disposition_type,
        status="PENDING",
        decided_by=decided_by,
    )
    session.add(disposition)
    await session.flush()
    return disposition


async def confirm_disposition(
    session: AsyncSession,
    disposition_id: str,
    final_proof_artifact_id: str,
    actor: str,
) -> DispositionRecord:
    disposition = await session.get(DispositionRecord, disposition_id)
    if not disposition:
        raise ValueError("disposition_not_found")
    if not final_proof_artifact_id:
        raise ValueError("proof_required")

    proof = await session.get(EvidenceArtifact, final_proof_artifact_id)
    if not proof:
        raise ValueError("proof_not_found")

    qualified = await is_vendor_qualified(session, disposition.vendor_id, at_date=date.today())
    if not qualified:
        raise ValueError("vendor_not_qualified")

    disposition.status = "CONFIRMED"
    disposition.final_proof_artifact_id = final_proof_artifact_id
    disposition.decided_by = actor
    await session.flush()
    return disposition
