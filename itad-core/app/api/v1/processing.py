from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.idempotency import check_idempotency, store_idempotency_response
from app.schemas.processing import (
    BatteryProcessingSessionCreate,
    BatteryProcessingSessionResponse,
    EwasteProcessingSessionCreate,
    EwasteProcessingSessionResponse,
)
from app.services.processing_service import (
    create_battery_processing_session,
    create_ewaste_processing_session,
    get_battery_processing_session,
    get_ewaste_processing_session,
)


router = APIRouter()


@router.post("/battery-processing-sessions", response_model=BatteryProcessingSessionResponse)
async def create_battery_processing_session_endpoint(
    payload: BatteryProcessingSessionCreate,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
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
        result = await create_battery_processing_session(
            db,
            payload,
            actor="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except ValueError as exc:
        detail = str(exc)
        if "BOL not found" in detail:
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=422, detail=detail)

    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body, 200, response_payload)
    return result


@router.get("/battery-processing-sessions/{session_id}", response_model=BatteryProcessingSessionResponse)
async def get_battery_processing_session_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await get_battery_processing_session(db, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="battery processing session not found")
    return result


@router.post("/ewaste-processing-sessions", response_model=EwasteProcessingSessionResponse)
async def create_ewaste_processing_session_endpoint(
    payload: EwasteProcessingSessionCreate,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
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
        result = await create_ewaste_processing_session(
            db,
            payload,
            actor="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except ValueError as exc:
        detail = str(exc)
        if "BOL not found" in detail:
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=422, detail=detail)

    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body, 200, response_payload)
    return result


@router.get("/ewaste-processing-sessions/{session_id}", response_model=EwasteProcessingSessionResponse)
async def get_ewaste_processing_session_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await get_ewaste_processing_session(db, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="ewaste processing session not found")
    return result
