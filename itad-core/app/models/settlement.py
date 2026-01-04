import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Numeric, Integer, CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Settlement(Base):
    __tablename__ = "settlement"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow, server_default="now()")
    created_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True)
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict, server_default="{}")

    __table_args__ = (Index("idx_settlement_bol_status", "bol_id", "status"),)


class SettlementPricingSnapshot(Base):
    __tablename__ = "settlement_pricing_snapshot"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id = Column(UUID(as_uuid=True), ForeignKey("settlement.id"), nullable=False)
    snapshot_no = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow, server_default="now()")
    created_by = Column(String, nullable=True)

    customer_pricing_profile_ref_id = Column(UUID(as_uuid=True), ForeignKey("pricing_external_ref.id"), nullable=True)
    service_catalog_ref_id = Column(UUID(as_uuid=True), ForeignKey("pricing_external_ref.id"), nullable=True)
    rate_card_ref_id = Column(UUID(as_uuid=True), ForeignKey("pricing_external_ref.id"), nullable=True)
    tier_ruleset_ref_id = Column(UUID(as_uuid=True), ForeignKey("pricing_external_ref.id"), nullable=True)

    pricing_payload_json = Column(JSON, nullable=False, default=dict, server_default="{}")
    basis_of_charge_json = Column(JSON, nullable=False, default=dict, server_default="{}")
    computed_lines_json = Column(JSON, nullable=False, default=lambda: {"lines": []}, server_default='{"lines":[]}')

    snapshot_hash_sha256 = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("snapshot_hash_sha256 ~ '^[0-9a-f]{64}$'", name="ck_settlement_snapshot_hash_format"),
        Index("uq_settlement_snapshot_no", "settlement_id", "snapshot_no", unique=True),
        Index("idx_settlement_snapshot_created", "settlement_id", "created_at"),
    )


class SettlementAdjustmentEvent(Base):
    __tablename__ = "settlement_adjustment_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id = Column(UUID(as_uuid=True), ForeignKey("settlement.id"), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow, server_default="now()")
    actor = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    currency = Column(String, nullable=False, default="USD", server_default="USD")
    reason_code = Column(String, nullable=False)
    reason_text = Column(String, nullable=False)
    approver = Column(String, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow, server_default="now()")
    related_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("settlement_pricing_snapshot.id"), nullable=True)
    payload_json = Column(JSON, nullable=False, default=dict, server_default="{}")

    __table_args__ = (
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_settlement_adjustment_currency"),
        Index("idx_settlement_adjustment", "settlement_id", "occurred_at"),
    )
