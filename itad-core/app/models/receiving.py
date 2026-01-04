import uuid
from sqlalchemy import Column, String, Text, Numeric, TIMESTAMP, Boolean, ForeignKey, func, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base


class ReceivingWeightRecordV3(Base):
    __tablename__ = "receiving_weight_record_v3"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False)
    container_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    gross_weight = Column(Numeric, nullable=False)
    tare_weight = Column(Numeric, nullable=False)
    net_weight = Column(Numeric, nullable=False)
    scale_id = Column(String, nullable=False)
    hazard_class = Column(String, nullable=True)
    un_number = Column(String, nullable=True)
    ddr_status = Column(Boolean, nullable=False)
    receiver_name = Column(String, nullable=False)
    receiver_employee_id = Column(String, nullable=False)
    receiver_signature_ref = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_void = Column(Boolean, default=False, nullable=False)
    void_reason = Column(Text, nullable=True)
    voided_record_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(String, nullable=True)
    material_received_as = Column(String, nullable=False)
    weight_unit = Column(String, nullable=False, default='LBS')
    receiver_signature_json = Column(JSONB, nullable=False)
    tare_source = Column(String, nullable=False)
    tare_profile_snapshot_json = Column(JSONB, nullable=True)
    tare_instance_snapshot_json = Column(JSONB, nullable=True)
    declared_gross_weight = Column(Numeric, nullable=True)
    declared_tare_weight = Column(Numeric, nullable=True)
    declared_net_weight = Column(Numeric, nullable=True)
    declared_weight_source = Column(String, nullable=True)
    reissue_of_id = Column(String, ForeignKey("receiving_weight_record_v3.id"), nullable=True)
