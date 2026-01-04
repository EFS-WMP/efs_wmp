import uuid
from sqlalchemy import Column, String, TIMESTAMP, func, Boolean, ForeignKey, JSON, Enum as SAEnum
from app.models.base import Base
from enum import Enum as PyEnum


class BolGateType(PyEnum):
    REQUIREMENTS_CONFIRMED = "REQUIREMENTS_CONFIRMED"
    PAPERWORK_VERIFIED = "PAPERWORK_VERIFIED"
    STAGING_ZONE_ASSIGNED = "STAGING_ZONE_ASSIGNED"
    RECEIVING_ANCHOR_RECORDED = "RECEIVING_ANCHOR_RECORDED"
    WORKSTREAMS_OPENED = "WORKSTREAMS_OPENED"
    BOL_CLOSED = "BOL_CLOSED"


class BolStageGate(Base):
    __tablename__ = "bol_stage_gates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    gate_type = Column(SAEnum(BolGateType, name="bolgatetype"), nullable=False)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    actor = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    is_void = Column(Boolean, nullable=False, default=False)
    void_reason = Column(String, nullable=True)
    voided_gate_id = Column(String, ForeignKey("bol_stage_gates.id"), nullable=True)
