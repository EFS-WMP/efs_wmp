import uuid
from sqlalchemy import Column, String, TIMESTAMP, func, ForeignKey
from app.models.base import Base
from enum import Enum as PyEnum


class WorkstreamType(PyEnum):
    BATTERY = "BATTERY"
    EWASTE = "EWASTE"


class WorkstreamStatus(PyEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VOIDED = "VOIDED"


class Workstream(Base):
    __tablename__ = "workstreams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    workstream_type = Column(String, nullable=False)
    status = Column(String, default=WorkstreamStatus.OPEN.value, nullable=False)
    opened_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    closed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    actor = Column(String, nullable=True)