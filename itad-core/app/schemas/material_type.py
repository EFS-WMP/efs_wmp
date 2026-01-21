"""
Phase 2.4: Material Type Schemas

Pydantic schemas for material types API.
Includes billing metadata fields (Phase 2.4a).
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class MaterialTypeResponse(BaseModel):
    """Material type response schema"""
    
    id: UUID
    code: str
    name: str
    stream: str
    hazard_class: str | None = None
    default_action: str | None = None
    requires_photo: bool
    requires_weight: bool
    is_active: bool
    # Phase 2.4a: Pricing state and billing metadata fields
    pricing_state: str = "unpriced"
    default_price: Decimal | None = None
    basis_of_charge: str | None = None
    gl_account_code: str | None = None
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "code": "BAT-LI-001",
                "name": "Lithium Batteries",
                "stream": "batteries",
                "hazard_class": "Class 9",
                "default_action": "recycle",
                "requires_photo": True,
                "requires_weight": True,
                "is_active": True,
                "pricing_state": "priced",
                "default_price": "0.1500",
                "basis_of_charge": "per_lb",
                "gl_account_code": "4100-100",
                "updated_at": "2026-01-17T20:00:00Z",
            }
        }
    }


class MaterialTypeListMeta(BaseModel):
    """Metadata for material types list response"""
    
    generated_at: str = Field(..., description="ISO8601 UTC timestamp when response was generated")
    count: int = Field(..., description="Number of items in response")
    include_inactive: bool = Field(..., description="Whether inactive records were included")
    updated_since: str | None = Field(None, description="ISO8601 timestamp filter applied, if any")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "generated_at": "2026-01-17T20:00:00Z",
                "count": 5,
                "include_inactive": True,
                "updated_since": None,
            }
        }
    }


class MaterialTypeListResponse(BaseModel):
    """Wrapper response for material types list endpoint"""
    
    items: list[MaterialTypeResponse] = Field(..., description="List of material types")
    meta: MaterialTypeListMeta = Field(..., description="Response metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "code": "BAT-LI-001",
                        "name": "Lithium Batteries",
                        "stream": "batteries",
                        "hazard_class": "Class 9",
                        "default_action": "recycle",
                        "requires_photo": True,
                        "requires_weight": True,
                        "is_active": True,
                        "updated_at": "2026-01-17T20:00:00Z",
                    }
                ],
                "meta": {
                    "generated_at": "2026-01-17T20:00:00Z",
                    "count": 1,
                    "include_inactive": True,
                    "updated_since": None,
                }
            }
        }
    }
