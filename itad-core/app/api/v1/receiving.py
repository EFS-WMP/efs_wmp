from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.config import settings
from app.core.idempotency import check_idempotency, store_idempotency_response
from app.schemas.receiving import ReceivingWeightRecordV3Create, ReceivingWeightRecordV3Response, ReceivingRecordVoidCreate, ReceivingRecordVoidResponse
from app.services.receiving_service import create_receiving_weight_record, get_receiving_record, void_receiving_record, reissue_receiving_record

router = APIRouter()


@router.post("/receiving-weight-records", response_model=ReceivingWeightRecordV3Response)
async def create_receiving_weight_record_endpoint(
    record_data: ReceivingWeightRecordV3Create,
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
    request_body = await request.body()
    request_body_str = request_body.decode()

    # Check idempotency
    cached = await check_idempotency(idempotency, route, method, request_body_str)
    if cached:
        return cached["body"]

    # Create record
    try:
        result = await create_receiving_weight_record(
            db,
            record_data,
            created_by="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Store idempotency
    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body_str, 200, response_payload)

    return result


@router.get("/receiving-weight-records/{record_id}", response_model=ReceivingWeightRecordV3Response, response_model_exclude_none=True)
async def get_receiving_weight_record_endpoint(
    record_id: str,
    request: Request,
    include_declared: bool = Query(False, description="Include declared weights when blind receiving is enabled"),
    db: AsyncSession = Depends(get_db),
):
    blind_receiving_enabled = settings.blind_receiving
    include_declared_allowed = True

    if blind_receiving_enabled:
        if include_declared:
            internal_role = request.headers.get("X-Internal-Role")
            if internal_role != "compliance_admin":
                raise HTTPException(status_code=403, detail="Declared weights require compliance_admin role")
            include_declared_allowed = True
        else:
            include_declared_allowed = False

    result = await get_receiving_record(
        db,
        record_id,
        blind_mode=blind_receiving_enabled,
        include_declared=include_declared_allowed,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Receiving record not found")
    return result


@router.post("/receiving-weight-records/{record_id}/void", response_model=ReceivingRecordVoidResponse)
async def void_receiving_weight_record_endpoint(
    record_id: str,
    void_data: ReceivingRecordVoidCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Ensure the record_id matches
    if void_data.receiving_record_id != record_id:
        raise HTTPException(status_code=400, detail="Record ID mismatch")
    try:
        result = await void_receiving_record(
            db,
            void_data,
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except ValueError as e:
        detail = str(e)
        if "not found" in detail:
            raise HTTPException(status_code=404, detail=detail)
        if "already voided" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=422, detail=detail)
    return result


@router.post("/receiving-weight-records/{record_id}/reissue", response_model=ReceivingWeightRecordV3Response)
async def reissue_receiving_weight_record_endpoint(
    record_id: str,
    reissue_data: ReceivingWeightRecordV3Create,
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
    request_body = await request.body()
    request_body_str = request_body.decode()

    # Check idempotency
    cached = await check_idempotency(idempotency, route, method, request_body_str)
    if cached:
        return cached["body"]

    # Reissue record
    try:
        result = await reissue_receiving_record(
            db,
            record_id,
            reissue_data,
            created_by="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except ValueError as e:
        detail = str(e)
        if "not found" in detail:
            raise HTTPException(status_code=404, detail=detail)
        if "must be voided" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=422, detail=detail)

    # Store idempotency
    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body_str, 200, response_payload)

    return result
