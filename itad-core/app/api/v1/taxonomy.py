from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.db import get_db
from app.core.idempotency import check_idempotency, store_idempotency_response
from app.schemas.taxonomy import TaxonomyItemCreate, TaxonomyItemResponse, TaxonomyTypeCreate, TaxonomyTypeResponse
from app.services.taxonomy_service import create_taxonomy_item, create_taxonomy_type, get_taxonomy_items, get_taxonomy_types


router = APIRouter()


def _require_compliance_admin(request: Request) -> None:
    if request.headers.get("X-Internal-Role") != "compliance_admin":
        raise HTTPException(status_code=403, detail="compliance_admin role required")


@router.get("/taxonomy/types", response_model=List[TaxonomyTypeResponse])
async def list_taxonomy_types(
    group_code: Optional[str] = None,
    active_at: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_taxonomy_types(db, group_code=group_code, active_at=active_at)


@router.get("/taxonomy/items", response_model=List[TaxonomyItemResponse])
async def list_taxonomy_items(
    group_code: Optional[str] = None,
    type_code: Optional[str] = None,
    sb20_flag: Optional[bool] = None,
    active_at: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_taxonomy_items(
        db,
        group_code=group_code,
        type_code=type_code,
        sb20_flag=sb20_flag,
        active_at=active_at,
    )


@router.post("/taxonomy/types", response_model=TaxonomyTypeResponse)
async def create_taxonomy_type_endpoint(
    payload: TaxonomyTypeCreate,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    _require_compliance_admin(request)
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    route = str(request.url.path)
    method = request.method
    request_body = (await request.body()).decode()

    cached = await check_idempotency(idempotency, route, method, request_body)
    if cached:
        return cached["body"]

    try:
        result = await create_taxonomy_type(
            db,
            payload,
            actor="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="taxonomy type already exists")

    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body, 200, response_payload)
    return result


@router.post("/taxonomy/items", response_model=TaxonomyItemResponse)
async def create_taxonomy_item_endpoint(
    payload: TaxonomyItemCreate,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    _require_compliance_admin(request)
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    route = str(request.url.path)
    method = request.method
    request_body = (await request.body()).decode()

    cached = await check_idempotency(idempotency, route, method, request_body)
    if cached:
        return cached["body"]

    try:
        result = await create_taxonomy_item(
            db,
            payload,
            actor="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="taxonomy item already exists")

    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body, 200, response_payload)
    return result
