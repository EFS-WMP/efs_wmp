import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    TIMESTAMP,
    UniqueConstraint,
    func,
    text,
)

from app.models.base import Base


class PickupManifest(Base):
    __tablename__ = "pickup_manifest"
    __table_args__ = (
        UniqueConstraint("manifest_no", name="uq_pickup_manifest_no"),
        UniqueConstraint("source_system", "manifest_fingerprint", name="uq_pickup_manifest_fingerprint"),
        CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','BOUND_TO_BOL','RECEIVED','CLOSED','VOIDED')",
            name="ck_pickup_manifest_status",
        ),
        CheckConstraint(
            "(status <> 'VOIDED') OR (void_reason IS NOT NULL)",
            name="ck_pickup_manifest_void_reason",
        ),
        Index("ix_pickup_manifest_status_submitted", "status", "submitted_at"),
        Index("ix_pickup_manifest_odoo_route", "odoo_day_route_id"),
        Index("ix_pickup_manifest_odoo_stop", "odoo_stop_id"),
        Index("ix_pickup_manifest_corr_id", "correlation_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    manifest_no = Column(String, nullable=False)
    status = Column(String, nullable=False)
    source_system = Column(String, nullable=False, server_default="ODOO")

    odoo_day_route_id = Column(String, nullable=True)
    odoo_stop_id = Column(String, nullable=True)
    odoo_pickup_occurrence_id = Column(String, nullable=True)
    odoo_work_order_id = Column(String, nullable=True)

    customer_id = Column(String, nullable=True)
    service_location_id = Column(String, nullable=True)

    route_snapshot_json = Column(JSON, nullable=False, server_default=text("'{}'::jsonb"))
    pod_evidence_json = Column(JSON, nullable=False, server_default=text("'{\"items\": []}'::jsonb"))

    manifest_fingerprint = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=True)

    correlation_id = Column(String, nullable=True)
    submitted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    submitted_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(String, nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)


class PickupManifestStateEvent(Base):
    __tablename__ = "pickup_manifest_state_event"
    __table_args__ = (
        Index("ix_pickup_manifest_state_event_manifest", "pickup_manifest_id", "occurred_at"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pickup_manifest_id = Column(String, ForeignKey("pickup_manifest.id"), nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    actor = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=False, server_default=text("'{}'::jsonb"))


class PickupManifestIntegrationAttempt(Base):
    __tablename__ = "pickup_manifest_integration_attempt"
    __table_args__ = (
        Index("ix_pickup_manifest_attempt_corr", "correlation_id", "occurred_at"),
        CheckConstraint(
            "outcome IN ('ACCEPTED','DUPLICATE_RETURNED','REJECTED','ERROR')",
            name="ck_pickup_manifest_attempt_outcome",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pickup_manifest_id = Column(String, ForeignKey("pickup_manifest.id"), nullable=True)
    source_system = Column(String, nullable=False, server_default="ODOO")
    correlation_id = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True)
    manifest_fingerprint = Column(String, nullable=True)
    outcome = Column(String, nullable=False)
    http_status = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    payload_json = Column(JSON, nullable=False, server_default=text("'{}'::jsonb"))


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"
    __table_args__ = (
        UniqueConstraint("address_hash", "effective_from", name="uq_geocode_cache_effective_from"),
        Index("ix_geocode_cache_hash_active", "address_hash", "is_active"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_geocode_confidence_range"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    address_hash = Column(String, nullable=False)
    normalized_address = Column(String, nullable=False)
    latitude = Column(Numeric, nullable=False)
    longitude = Column(Numeric, nullable=False)
    provider = Column(String, nullable=False)
    confidence = Column(Numeric, nullable=False)
    result_json = Column(JSON, nullable=False, server_default=text("'{}'::jsonb"))
    effective_from = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    effective_to = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(String, nullable=True)
