from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_events import DomainEvent
from app.models.taxonomy import TaxonomyChangeLog, TaxonomyItem, TaxonomyType
from app.schemas.taxonomy import TaxonomyItemCreate, TaxonomyItemResponse, TaxonomyTypeCreate, TaxonomyTypeResponse


async def create_taxonomy_type(
    db: AsyncSession,
    data: TaxonomyTypeCreate,
    actor: str,
    request_id: str,
    correlation_id: str,
) -> TaxonomyTypeResponse:
    taxonomy_type = TaxonomyType(
        group_code=data.group_code,
        type_code=data.type_code,
        type_name=data.type_name,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        is_active=data.is_active,
    )
    db.add(taxonomy_type)
    await db.commit()
    await db.refresh(taxonomy_type)

    payload = {
        "group_code": taxonomy_type.group_code,
        "type_code": taxonomy_type.type_code,
        "type_name": taxonomy_type.type_name,
        "effective_from": taxonomy_type.effective_from.isoformat(),
        "effective_to": taxonomy_type.effective_to.isoformat() if taxonomy_type.effective_to else None,
    }
    change_log = TaxonomyChangeLog(
        actor=actor,
        action_type="CREATE",
        entity_type="TYPE",
        entity_id=taxonomy_type.id,
        payload_json=payload,
    )
    db.add(change_log)

    event = DomainEvent(
        actor=actor,
        entity_type="TAXONOMY_TYPE",
        entity_id=taxonomy_type.id,
        event_type="TAXONOMY_TYPE_CREATED",
        payload_json=payload,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return TaxonomyTypeResponse(
        id=taxonomy_type.id,
        group_code=taxonomy_type.group_code,
        type_code=taxonomy_type.type_code,
        type_name=taxonomy_type.type_name,
        effective_from=taxonomy_type.effective_from,
        effective_to=taxonomy_type.effective_to,
        is_active=taxonomy_type.is_active,
    )


async def create_taxonomy_item(
    db: AsyncSession,
    data: TaxonomyItemCreate,
    actor: str,
    request_id: str,
    correlation_id: str,
) -> TaxonomyItemResponse:
    taxonomy_item = TaxonomyItem(
        taxonomy_type_id=data.taxonomy_type_id,
        variant_code=data.variant_code,
        variant_name=data.variant_name,
        sb20_flag=data.sb20_flag,
        hazard_class=data.hazard_class,
        un_number=data.un_number,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        is_active=data.is_active,
    )
    db.add(taxonomy_item)
    await db.commit()
    await db.refresh(taxonomy_item)

    payload = {
        "taxonomy_type_id": taxonomy_item.taxonomy_type_id,
        "variant_code": taxonomy_item.variant_code,
        "variant_name": taxonomy_item.variant_name,
        "sb20_flag": taxonomy_item.sb20_flag,
        "effective_from": taxonomy_item.effective_from.isoformat(),
        "effective_to": taxonomy_item.effective_to.isoformat() if taxonomy_item.effective_to else None,
    }
    change_log = TaxonomyChangeLog(
        actor=actor,
        action_type="CREATE",
        entity_type="ITEM",
        entity_id=taxonomy_item.id,
        payload_json=payload,
    )
    db.add(change_log)

    event = DomainEvent(
        actor=actor,
        entity_type="TAXONOMY_ITEM",
        entity_id=taxonomy_item.id,
        event_type="TAXONOMY_ITEM_CREATED",
        payload_json=payload,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.commit()

    return TaxonomyItemResponse(
        id=taxonomy_item.id,
        taxonomy_type_id=taxonomy_item.taxonomy_type_id,
        variant_code=taxonomy_item.variant_code,
        variant_name=taxonomy_item.variant_name,
        sb20_flag=taxonomy_item.sb20_flag,
        hazard_class=taxonomy_item.hazard_class,
        un_number=taxonomy_item.un_number,
        effective_from=taxonomy_item.effective_from,
        effective_to=taxonomy_item.effective_to,
        is_active=taxonomy_item.is_active,
    )


def _apply_active_at_filter(query, model, active_at: Optional[datetime]):
    if active_at is None:
        return query.where(model.is_active.is_(True))
    return query.where(
        model.is_active.is_(True),
        model.effective_from <= active_at,
        (model.effective_to.is_(None) | (model.effective_to > active_at)),
    )


async def get_taxonomy_types(
    db: AsyncSession,
    group_code: Optional[str] = None,
    active_at: Optional[datetime] = None,
) -> List[TaxonomyTypeResponse]:
    query = select(TaxonomyType)
    if group_code:
        query = query.where(TaxonomyType.group_code == group_code)
    query = _apply_active_at_filter(query, TaxonomyType, active_at)
    result = await db.execute(query)
    types = result.scalars().all()
    return [
        TaxonomyTypeResponse(
            id=taxonomy_type.id,
            group_code=taxonomy_type.group_code,
            type_code=taxonomy_type.type_code,
            type_name=taxonomy_type.type_name,
            effective_from=taxonomy_type.effective_from,
            effective_to=taxonomy_type.effective_to,
            is_active=taxonomy_type.is_active,
        )
        for taxonomy_type in types
    ]


async def get_taxonomy_items(
    db: AsyncSession,
    group_code: Optional[str] = None,
    type_code: Optional[str] = None,
    sb20_flag: Optional[bool] = None,
    active_at: Optional[datetime] = None,
) -> List[TaxonomyItemResponse]:
    query = select(TaxonomyItem).join(TaxonomyType, TaxonomyItem.taxonomy_type_id == TaxonomyType.id)
    if group_code:
        query = query.where(TaxonomyType.group_code == group_code)
    if type_code:
        query = query.where(TaxonomyType.type_code == type_code)
    if sb20_flag is not None:
        query = query.where(TaxonomyItem.sb20_flag == sb20_flag)
    query = _apply_active_at_filter(query, TaxonomyItem, active_at)
    query = query.where(TaxonomyType.is_active.is_(True))
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        TaxonomyItemResponse(
            id=item.id,
            taxonomy_type_id=item.taxonomy_type_id,
            variant_code=item.variant_code,
            variant_name=item.variant_name,
            sb20_flag=item.sb20_flag,
            hazard_class=item.hazard_class,
            un_number=item.un_number,
            effective_from=item.effective_from,
            effective_to=item.effective_to,
            is_active=item.is_active,
        )
        for item in items
    ]
