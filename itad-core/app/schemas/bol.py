from pydantic import BaseModel
from typing import Optional
from app.models.bol import SourceType, Status


class BOLCreate(BaseModel):
    bol_number: Optional[str] = None
    source_type: SourceType
    customer_snapshot_json: dict
    requirement_profile_snapshot_json: Optional[dict] = None
    requirement_profile_version: Optional[str] = None
    requirement_profile_effective_from: Optional[str] = None


class BOLResponse(BaseModel):
    id: str
    bol_number: str
    source_type: SourceType
    customer_snapshot_json: dict
    requirement_profile_snapshot_json: Optional[dict]
    requirement_profile_version: Optional[str]
    requirement_profile_effective_from: Optional[str]
    status: Status
    created_at: str
    created_by: Optional[str]