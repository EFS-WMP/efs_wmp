from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ReceivingWeightRecordV3Create(BaseModel):
    bol_id: str
    occurred_at: datetime
    material_received_as: str
    container_type: str
    quantity: int = Field(..., gt=0)
    gross_weight: float = Field(..., ge=0)
    tare_weight: float = Field(..., ge=0)
    net_weight: float = Field(..., ge=0)
    weight_unit: str = "LBS"
    scale_id: str
    un_number: Optional[str] = None
    hazard_class: Optional[str] = None
    ddr_status: bool
    receiver_employee_id: str
    receiver_name: str
    receiver_signature_json: Dict[str, Any]
    receiver_signature_ref: Optional[str] = None
    notes: Optional[str] = None
    tare_source: str
    tare_profile_snapshot_json: Optional[Dict[str, Any]] = None
    tare_instance_snapshot_json: Optional[Dict[str, Any]] = None
    declared_gross_weight: Optional[float] = None
    declared_tare_weight: Optional[float] = None
    declared_net_weight: Optional[float] = None
    declared_weight_source: Optional[str] = None
    reissue_of_id: Optional[str] = None


class ReceivingWeightRecordV3Response(BaseModel):
    id: str
    bol_id: str
    occurred_at: datetime
    material_received_as: str
    container_type: str
    quantity: int
    gross_weight: float
    tare_weight: float
    net_weight: float
    weight_unit: str
    scale_id: str
    un_number: Optional[str]
    hazard_class: Optional[str]
    ddr_status: bool
    receiver_employee_id: str
    receiver_name: str
    receiver_signature_json: Dict[str, Any]
    receiver_signature_ref: Optional[str]
    notes: Optional[str]
    is_void: bool
    void_reason: Optional[str]
    voided_record_id: Optional[str]
    created_at: str
    created_by: Optional[str]
    tare_source: str
    tare_profile_snapshot_json: Optional[Dict[str, Any]]
    tare_instance_snapshot_json: Optional[Dict[str, Any]]
    declared_gross_weight: Optional[float]
    declared_tare_weight: Optional[float]
    declared_net_weight: Optional[float]
    declared_weight_source: Optional[str]
    reissue_of_id: Optional[str]


class ReceivingRecordVoidCreate(BaseModel):
    receiving_record_id: str
    void_reason: str
    voided_by: str


class ReceivingRecordVoidResponse(BaseModel):
    id: str
    receiving_record_id: str
    void_reason: str
    voided_by: str
    voided_at: datetime
