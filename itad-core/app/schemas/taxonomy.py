from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaxonomyTypeCreate(BaseModel):
    group_code: str
    type_code: str
    type_name: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
    is_active: bool = True


class TaxonomyTypeResponse(BaseModel):
    id: str
    group_code: str
    type_code: str
    type_name: str
    effective_from: datetime
    effective_to: Optional[datetime]
    is_active: bool


class TaxonomyItemCreate(BaseModel):
    taxonomy_type_id: str
    variant_code: str
    variant_name: str
    sb20_flag: bool = False
    hazard_class: Optional[str] = None
    un_number: Optional[str] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    is_active: bool = True


class TaxonomyItemResponse(BaseModel):
    id: str
    taxonomy_type_id: str
    variant_code: str
    variant_name: str
    sb20_flag: bool
    hazard_class: Optional[str]
    un_number: Optional[str]
    effective_from: datetime
    effective_to: Optional[datetime]
    is_active: bool
