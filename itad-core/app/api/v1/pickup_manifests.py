from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.pickup_manifest import (
    PickupManifestResponse,
    PickupManifestSubmitRequest,
    PickupManifestSubmitResponse,
)
from app.services.pickup_manifest_service import (
    get_pickup_manifest_chain,
    submit_pickup_manifest,
)

router = APIRouter()


def _validate_no_operational_truth_fields(payload: dict) -> None:
    """
    SoR Guard: Reject payloads containing dispatch/route execution truth fields.
    Odoo18 is the dispatch system-of-record; ITAD Core must not accept/store dispatch state.
    
    Recursively scans the payload, but EXEMPTS snapshot fields from inspection.
    Snapshot fields (keys ending with "_snapshot_json" or exactly "snapshot_json") are 
    allowed to contain any data because they are read-only archives, not operational state.
    
    Forbidden operational-truth fields (checked outside snapshots):
    - dispatch_status, dispatch_priority
    - stop_execution, route_execution, driver_assignment
    - eta, actual_arrival, actual_departure
    - actual_delivery_time, actual_pickup_time, route_state, stop_sequence
    """
    forbidden_fields = {
        "dispatch_status",
        "dispatch_priority",
        "stop_execution",
        "route_execution",
        "driver_assignment",
        "eta",
        "actual_arrival",
        "actual_departure",
        "actual_delivery_time",
        "actual_pickup_time",
        "route_state",
        "stop_sequence",
    }
    
    def is_snapshot_field(key: str) -> bool:
        """Check if a field is a snapshot field that should be exempted from scanning."""
        key_lower = key.lower()
        return key_lower == "snapshot_json" or key_lower.endswith("_snapshot_json")
    
    def scan_value(obj, path: str = "") -> None:
        """Recursively scan object, but skip snapshot fields."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Skip scanning into snapshot fields entirely
                if is_snapshot_field(key):
                    continue
                
                # Check if this key is forbidden
                key_lower = key.lower()
                for forbidden in forbidden_fields:
                    if forbidden.lower() in key_lower:
                        raise ValueError(
                            f"Forbidden operational truth field '{key}' found at '{current_path}'. "
                            f"Odoo18 is the dispatch SoR; ITAD Core does not accept dispatch state."
                        )
                
                # Recurse into nested dicts and lists
                if isinstance(value, (dict, list)):
                    scan_value(value, current_path)
        
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                scan_value(item, f"{path}[{idx}]")
    
    # Convert payload to dict if needed
    payload_dict = payload if isinstance(payload, dict) else payload.model_dump()
    
    # Scan the entire payload, respecting snapshot exemptions
    scan_value(payload_dict)


@router.post("/pickup-manifests:submit", response_model=PickupManifestSubmitResponse)
async def submit_pickup_manifest_endpoint(
    payload: PickupManifestSubmitRequest,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    idempotency = idempotency_key_header or idempotency_key
    if not idempotency:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")

    # SoR Guard: Reject operational truth fields
    try:
        _validate_no_operational_truth_fields(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        manifest, bol, outcome, geocode_gate = await submit_pickup_manifest(
            db,
            payload,
            idempotency_key=idempotency,
            actor="api",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="internal_error")

    return PickupManifestSubmitResponse(
        pickup_manifest_id=manifest.id,
        manifest_no=manifest.manifest_no,
        status=manifest.status,
        bol_id=bol.id,
        geocode_gate=geocode_gate,
    )



@router.get(
    "/pickup-manifests/{pickup_manifest_id}",
    response_model=PickupManifestResponse,
)
async def get_pickup_manifest(
    pickup_manifest_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        manifest, bol_id, receiving_id, geocode_gate = await get_pickup_manifest_chain(
            db, pickup_manifest_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Derive status: if manifest.status is SUBMITTED and a PICKUP BOL exists, return BOUND_TO_BOL
    response_status = manifest.status
    if manifest.status == "SUBMITTED" and bol_id:
        response_status = "BOUND_TO_BOL"

    return PickupManifestResponse(
        pickup_manifest_id=manifest.id,
        manifest_no=manifest.manifest_no,
        status=response_status,
        bol_id=bol_id,
        receiving_id=receiving_id,
        geocode_gate=geocode_gate,
    )
