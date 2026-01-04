import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, JSON, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class PricingExternalRef(Base):
    __tablename__ = "pricing_external_ref"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    ref_type = Column(String, nullable=False)
    odoo_record_model = Column(String, nullable=False)
    odoo_record_id = Column(String, nullable=False)
    odoo_version = Column(String, nullable=True)
    ref_hash_sha256 = Column(String, nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow, server_default="now()")
    created_by = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict, server_default="{}")

    __table_args__ = (
        CheckConstraint("ref_hash_sha256 ~ '^[0-9a-f]{64}$'", name="ck_pricing_external_ref_hash_format"),
        Index("idx_pricing_external_ref_customer_type_active", "customer_id", "ref_type", "is_active"),
        Index("uq_pricing_external_ref_unique", "ref_type", "odoo_record_model", "odoo_record_id", "effective_from", unique=True),
    )
