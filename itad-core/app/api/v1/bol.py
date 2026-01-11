from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.db import get_db
from app.core.idempotency import check_idempotency, store_idempotency_response
from app.schemas.bol import BOLCreate, BOLResponse
from app.services.bol_service import create_bol, append_bol_gate, get_bol_state, confirm_requirements, close_bol, create_workstreams
from app.models.bol_stage_gates import BolGateType
from pydantic import BaseModel
from typing import Dict, Any, List


class GateAppendRequest(BaseModel):
    gate_type: str
    payload: Dict[str, Any] = {}


class RequirementsConfirmRequest(BaseModel):
    requires_battery_processing: bool
    requires_ewaste_processing: bool
    rationale: str


router = APIRouter()

router = APIRouter()


@router.post("/bol", response_model=BOLResponse)
async def create_bol_endpoint(
    bol_data: BOLCreate,
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

    # Create BOL
    try:
        result = await create_bol(
            db,
            bol_data,
            created_by="api",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="BOL number already exists")

    # Store idempotency
    response_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
    await store_idempotency_response(idempotency, route, method, request_body_str, 200, response_payload)

    return result


@router.get("/bol/{bol_id}", response_model=BOLResponse)
async def get_bol(bol_id: str, db: AsyncSession = Depends(get_db)):
    # Placeholder for get
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/bol/{bol_id}/gates")
async def append_bol_gate_endpoint(
    bol_id: str,
    gate_data: GateAppendRequest,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    
    try:
        gate_type = BolGateType(gate_data.gate_type)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid gate_type")
    
    try:
        gate = await append_bol_gate(
            db, bol_id, gate_type, "api", gate_data.payload,
            request.state.request_id, request.state.correlation_id
        )
        return {"id": gate.id, "gate_type": gate.gate_type.value}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/bol/{bol_id}/state")
async def get_bol_state_endpoint(bol_id: str, db: AsyncSession = Depends(get_db)):
    try:
        state = await get_bol_state(db, bol_id)
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bol/{bol_id}/requirements/confirm")
async def confirm_requirements_endpoint(
    bol_id: str,
    req_data: RequirementsConfirmRequest,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    
    try:
        await confirm_requirements(
            db, bol_id, req_data.requires_battery_processing, req_data.requires_ewaste_processing,
            req_data.rationale, "api", request.state.request_id, request.state.correlation_id
        )
        return {"status": "confirmed"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/bol/{bol_id}/close")
async def close_bol_endpoint(
    bol_id: str,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    
    try:
        await close_bol(db, bol_id, "api", request.state.request_id, request.state.correlation_id)
        return {"status": "closed"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/bol/{bol_id}/workstreams")
async def create_workstreams_endpoint(
    bol_id: str,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    
    try:
        workstreams = await create_workstreams(db, bol_id, "api", request.state.request_id, request.state.correlation_id)
        return {"workstreams": [{"id": ws.id, "type": ws.workstream_type.value} for ws in workstreams]}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
