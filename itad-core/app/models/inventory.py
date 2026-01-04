import uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    JSON,
    Numeric,
    String,
    TIMESTAMP,
    UniqueConstraint,
    CheckConstraint,
    BigInteger,
    func,
)

from app.models.base import Base


class WarehouseLocation(Base):
    __tablename__ = "warehouse_location"
    __table_args__ = (
        UniqueConstraint("site_code", "location_code", name="uq_location_site_code"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    site_code = Column(String, nullable=False)
    location_code = Column(String, nullable=False)
    location_name = Column(String, nullable=False)
    location_type = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)


class LpnContainer(Base):
    __tablename__ = "lpn_container"
    __table_args__ = (
        UniqueConstraint("lpn_code", name="uq_lpn_code"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lpn_code = Column(String, nullable=False)
    container_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_location_id = Column(String, ForeignKey("warehouse_location.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)


class InventoryLot(Base):
    __tablename__ = "inventory_lot"
    __table_args__ = (
        UniqueConstraint("lot_code", name="uq_lot_code"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_code = Column(String, nullable=False)
    bol_id = Column(String, ForeignKey("bol.id"), nullable=True)
    taxonomy_item_id = Column(String, ForeignKey("taxonomy_item.id"), nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    effective_weight_lbs = Column(Numeric, nullable=True)
    metadata_json = Column(JSON, nullable=False, server_default="{}")
    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)


class LotLpnMembership(Base):
    __tablename__ = "lot_lpn_membership"
    __table_args__ = (
        UniqueConstraint("lot_id", "lpn_id", "added_at", name="uq_lot_lpn_added"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_id = Column(String, ForeignKey("inventory_lot.id"), nullable=False)
    lpn_id = Column(String, ForeignKey("lpn_container.id"), nullable=False)
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    added_by = Column(String, nullable=True)
    removed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    removed_by = Column(String, nullable=True)
    remove_reason = Column(String, nullable=True)


class OutboundShipment(Base):
    __tablename__ = "outbound_shipment"
    __table_args__ = (
        UniqueConstraint("shipment_no", name="uq_shipment_no"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipment_no = Column(String, nullable=False)
    status = Column(String, nullable=False)
    carrier_name = Column(String, nullable=True)
    carrier_scac = Column(String, nullable=True)
    vehicle_plate = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    appointment_at = Column(TIMESTAMP(timezone=True), nullable=True)
    seal_number = Column(String, nullable=True)
    hazmat_flag = Column(Boolean, nullable=False, default=False)
    origin_site_code = Column(String, nullable=False)
    destination_vendor_id = Column(String, ForeignKey("downstream_vendor.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, server_default="{}")


class ShipmentLpn(Base):
    __tablename__ = "shipment_lpn"
    __table_args__ = (
        UniqueConstraint("shipment_id", "lpn_id", name="uq_shipment_lpn"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipment_id = Column(String, ForeignKey("outbound_shipment.id"), nullable=False)
    lpn_id = Column(String, ForeignKey("lpn_container.id"), nullable=False)
    loaded_at = Column(TIMESTAMP(timezone=True), nullable=True)
    loaded_by = Column(String, nullable=True)
    unloaded_at = Column(TIMESTAMP(timezone=True), nullable=True)
    unloaded_by = Column(String, nullable=True)


class DownstreamVendor(Base):
    __tablename__ = "downstream_vendor"
    __table_args__ = (
        UniqueConstraint("vendor_code", name="uq_vendor_code"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_code = Column(String, nullable=False)
    vendor_name = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    allowlist_flag = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, server_default="{}")


class VendorCertification(Base):
    __tablename__ = "vendor_certification"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("downstream_vendor.id"), nullable=False)
    cert_type = Column(String, nullable=False)
    cert_number = Column(String, nullable=True)
    issued_at = Column(String, nullable=True)
    expires_at = Column(String, nullable=True)
    effective_from = Column(String, nullable=False)
    effective_to = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    artifact_id = Column(String, ForeignKey("evidence_artifact.id"), nullable=True)


class DispositionRecord(Base):
    __tablename__ = "disposition_record"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_id = Column(String, ForeignKey("inventory_lot.id"), nullable=False)
    vendor_id = Column(String, ForeignKey("downstream_vendor.id"), nullable=False)
    shipment_id = Column(String, ForeignKey("outbound_shipment.id"), nullable=True)
    disposition_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    decided_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    decided_by = Column(String, nullable=True)
    final_proof_artifact_id = Column(String, ForeignKey("evidence_artifact.id"), nullable=True)
    metadata_json = Column(JSON, nullable=False, server_default="{}")
    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)
