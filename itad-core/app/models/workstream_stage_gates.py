import uuid
from sqlalchemy import Column, String, TIMESTAMP, func, Boolean, ForeignKey, JSON, Enum as SAEnum
from app.models.base import Base
from enum import Enum as PyEnum


class WorkstreamGateType(PyEnum):
    WORKSTREAM_OPENED = "WORKSTREAM_OPENED"
    WORKSTREAM_STARTED = "WORKSTREAM_STARTED"
    WORKSTREAM_COMPLETED = "WORKSTREAM_COMPLETED"
    WORKSTREAM_VOIDED = "WORKSTREAM_VOIDED"


class WorkstreamStageGate(Base):
    __tablename__ = "workstream_stage_gates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workstream_id = Column(String, ForeignKey("workstreams.id"), nullable=False)
    gate_type = Column(SAEnum(WorkstreamGateType, name="workstreamgatetype"), nullable=False)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    actor = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    is_void = Column(Boolean, nullable=False, default=False)
    void_reason = Column(String, nullable=True)
    voided_gate_id = Column(String, ForeignKey("workstream_stage_gates.id"), nullable=True)
