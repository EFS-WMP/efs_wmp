from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.idempotency import check_idempotency, store_idempotency_response
from app.services.bol_service import append_workstream_gate
from app.models.workstream_stage_gates import WorkstreamGateType
from pydantic import BaseModel
from typing import Dict, Any


class WorkstreamGateAppendRequest(BaseModel):
    gate_type: str
    payload: Dict[str, Any] = {}


router = APIRouter()


@router.post("/workstreams/{workstream_id}/gates")
async def append_workstream_gate_endpoint(
    workstream_id: str,
    gate_data: WorkstreamGateAppendRequest,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    
    try:
        gate_type = WorkstreamGateType(gate_data.gate_type)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid gate_type")
    
    try:
        gate = await append_workstream_gate(
            db, workstream_id, gate_type, "api", gate_data.payload,
            request.state.request_id, request.state.correlation_id
        )
        return {"id": gate.id, "gate_type": gate.gate_type.value}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
