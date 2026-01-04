import datetime
import hashlib
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import PricingExternalRef


async def upsert_pricing_external_ref(
    session: AsyncSession,
    ref_type: str,
    odoo_record_model: str,
    odoo_record_id: str,
    ref_hash_sha256: str,
    effective_from: datetime.datetime,
    effective_to: Optional[datetime.datetime],
    customer_id: Optional[str] = None,
    odoo_version: Optional[str] = None,
    approved_at: Optional[datetime.datetime] = None,
    approved_by: Optional[str] = None,
    actor: Optional[str] = None,
    metadata_json: Optional[dict] = None,
) -> PricingExternalRef:
    # end-date existing active refs for the same Odoo object
    existing = await session.execute(
        select(PricingExternalRef).where(
            PricingExternalRef.ref_type == ref_type,
            PricingExternalRef.odoo_record_model == odoo_record_model,
            PricingExternalRef.odoo_record_id == odoo_record_id,
            PricingExternalRef.is_active.is_(True),
        )
    )
    for row in existing.scalars().all():
        row.is_active = False
        row.effective_to = effective_from

    record = PricingExternalRef(
        customer_id=customer_id,
        ref_type=ref_type,
        odoo_record_model=odoo_record_model,
        odoo_record_id=odoo_record_id,
        odoo_version=odoo_version,
        ref_hash_sha256=ref_hash_sha256,
        effective_from=effective_from,
        effective_to=effective_to,
        is_active=True,
        approved_at=approved_at,
        approved_by=approved_by,
        created_by=actor,
        metadata_json=metadata_json or {},
    )
    session.add(record)
    await session.flush()
    return record
