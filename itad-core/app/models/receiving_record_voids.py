import uuid
from sqlalchemy import Column, String, TIMESTAMP, func, ForeignKey
from app.models.base import Base


class ReceivingRecordVoid(Base):
    __tablename__ = "receiving_record_voids"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    receiving_record_id = Column(String, ForeignKey("receiving_weight_record_v3.id"), nullable=False)
    void_reason = Column(String, nullable=False)
    voided_by = Column(String, nullable=False)
    voided_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)