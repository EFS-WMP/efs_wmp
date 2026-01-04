import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, JSON, String, TIMESTAMP, func, CheckConstraint, ForeignKey
from app.models.base import Base


class SourceType(PyEnum):
    INBOUND_TRUCK = "INBOUND_TRUCK"
    DROP_OFF = "DROP_OFF"
    MAIL_BACK = "MAIL_BACK"
    INTER_COMPANY = "INTER_COMPANY"
    RMA = "RMA"
    PICKUP = "PICKUP"


class Status(PyEnum):
    OPEN = "OPEN"
    IN_DISPUTE = "IN_DISPUTE"
    READY_FOR_OUTBOUND = "READY_FOR_OUTBOUND"
    CLOSED = "CLOSED"


class BOL(Base):
    __tablename__ = "bol"
    __table_args__ = (
        CheckConstraint(
            f"source_type IN ({', '.join(repr(e.value) for e in SourceType)})",
            name="ck_bol_source_type",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(e.value) for e in Status)})",
            name="ck_bol_status",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_number = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False, default=SourceType.PICKUP.value)
    customer_snapshot_json = Column(JSON, nullable=False)
    requirement_profile_snapshot_json = Column(JSON, nullable=True)
    status = Column(String, default=Status.OPEN.value, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(String, nullable=True)
    requirement_profile_version = Column(String, nullable=True)
    requirement_profile_effective_from = Column(TIMESTAMP(timezone=True), nullable=True)
    requires_battery_processing = Column(Boolean, nullable=False, default=False)
    requires_ewaste_processing = Column(Boolean, nullable=False, default=False)
    requirements_locked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    pickup_manifest_id = Column(String, ForeignKey("pickup_manifest.id"), nullable=True, unique=True)
