from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BatteryProcessingLineCreate(BaseModel):
    taxonomy_item_id: str
    weight_lbs: float = Field(..., ge=0)
    quantity: Optional[int] = Field(None, gt=0)
    contamination_flag: bool = False
    contamination_taxonomy_item_id: Optional[str] = None
    notes: Optional[str] = None


class BatteryProcessingSessionCreate(BaseModel):
    bol_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    headcount: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = None
    lines: List[BatteryProcessingLineCreate]


class BatteryProcessingLineResponse(BaseModel):
    id: str
    taxonomy_item_id: str
    weight_lbs: float
    quantity: Optional[int]
    contamination_flag: bool
    contamination_taxonomy_item_id: Optional[str]
    notes: Optional[str]


class BatteryProcessingSessionResponse(BaseModel):
    id: str
    bol_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    headcount: Optional[int]
    notes: Optional[str]
    lines: List[BatteryProcessingLineResponse]


class EwasteProcessingLineCreate(BaseModel):
    taxonomy_item_id: str
    weight_lbs: float = Field(..., ge=0)
    quantity: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = None


class EwasteProcessingSessionCreate(BaseModel):
    bol_id: str
    started_at: datetime
    ended_at: datetime
    headcount: int = Field(..., gt=0)
    notes: Optional[str] = None
    lines: List[EwasteProcessingLineCreate]


class EwasteProcessingLineResponse(BaseModel):
    id: str
    taxonomy_item_id: str
    weight_lbs: float
    quantity: Optional[int]
    notes: Optional[str]


class EwasteProcessingSessionResponse(BaseModel):
    id: str
    bol_id: str
    started_at: datetime
    ended_at: datetime
    headcount: int
    notes: Optional[str]
    lines: List[EwasteProcessingLineResponse]
    productivity_lbs_per_hour: Optional[float] = None
