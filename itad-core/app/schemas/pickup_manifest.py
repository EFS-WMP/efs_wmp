from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class PickupManifestSubmitRequest(BaseModel):
    model_config = {"extra": "allow"}
    
    source_system: str
    manifest_fingerprint: str
    completed_at: str
    odoo_refs: Optional[dict[str, str | None]] = None
    route_snapshot_json: Optional[dict[str, Any]] = None
    location_snapshot_json: Optional[dict[str, Any]] = None
    pod_evidence: list[dict[str, Any]] = Field(default_factory=list)
    
    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, data):
        """Normalize incoming payload to canonical format.
        
        Accepts both:
        - Nested: odoo_refs={...}, route_snapshot_json={...}, location_snapshot_json={...}, pod_evidence=[...]
        - Flat: odoo_day_route_id=..., route_snapshot={...}, location_snapshot={...}, pod_evidence_items=[...]
        
        Normalizes to nested format before validation.
        """
        if not isinstance(data, dict):
            return data
        
        # Make a copy to avoid modifying input
        normalized = dict(data)
        
        # Normalize odoo_refs: if flat fields present, build from them
        if "odoo_refs" not in normalized or normalized["odoo_refs"] is None:
            odoo_refs = {
                "odoo_day_route_id": normalized.get("odoo_day_route_id"),
                "odoo_stop_id": normalized.get("odoo_stop_id"),
                "odoo_pickup_occurrence_id": normalized.get("odoo_pickup_occurrence_id"),
                "odoo_work_order_id": normalized.get("odoo_work_order_id"),
                "customer_id": normalized.get("customer_id"),
                "service_location_id": normalized.get("service_location_id"),
            }
            normalized["odoo_refs"] = odoo_refs
        
        # Normalize snapshot keys
        if "route_snapshot_json" not in normalized or normalized["route_snapshot_json"] is None:
            normalized["route_snapshot_json"] = normalized.get("route_snapshot")
        
        if "location_snapshot_json" not in normalized or normalized["location_snapshot_json"] is None:
            normalized["location_snapshot_json"] = normalized.get("location_snapshot")
        
        # Normalize pod_evidence
        if "pod_evidence" not in normalized or not normalized["pod_evidence"]:
            normalized["pod_evidence"] = normalized.get("pod_evidence_items") or []
        
        return normalized


class PickupManifestSubmitResponse(BaseModel):
    pickup_manifest_id: str
    manifest_no: str
    status: str
    bol_id: str
    geocode_gate: Optional[str] = None


class PickupManifestResponse(BaseModel):
    pickup_manifest_id: str
    manifest_no: str
    status: str
    bol_id: Optional[str] = None
    receiving_id: Optional[str] = None
    geocode_gate: Optional[str] = None
