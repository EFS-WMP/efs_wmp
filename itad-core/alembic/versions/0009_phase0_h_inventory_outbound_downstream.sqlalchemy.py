"""phase0_h inventory outbound downstream data layer

Revision ID: 0009
Revises: 0008
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouse_location",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("site_code", sa.String(), nullable=False),
        sa.Column("location_code", sa.String(), nullable=False),
        sa.Column("location_name", sa.String(), nullable=False),
        sa.Column("location_type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_code", "location_code", name="uq_location_site_code"),
    )
    op.create_index("ix_warehouse_location_site_type", "warehouse_location", ["site_code", "location_type", "is_active"])

    op.create_table(
        "lpn_container",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("lpn_code", sa.String(), nullable=False),
        sa.Column("container_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_location_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["current_location_id"], ["warehouse_location.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lpn_code", name="uq_lpn_code"),
    )
    op.create_index("ix_lpn_status", "lpn_container", ["status"])
    op.create_index("ix_lpn_current_location", "lpn_container", ["current_location_id"])

    op.create_table(
        "inventory_lot",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("lot_code", sa.String(), nullable=False),
        sa.Column("bol_id", sa.String(), nullable=True),
        sa.Column("taxonomy_item_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("effective_weight_lbs", sa.Numeric(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["bol_id"], ["bol.id"]),
        sa.ForeignKeyConstraint(["taxonomy_item_id"], ["taxonomy_item.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_code", name="uq_lot_code"),
    )
    op.create_index("ix_inventory_lot_status", "inventory_lot", ["status"])
    op.create_index("ix_inventory_lot_taxonomy", "inventory_lot", ["taxonomy_item_id"])

    op.create_table(
        "lot_lpn_membership",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("lot_id", sa.String(), nullable=False),
        sa.Column("lpn_id", sa.String(), nullable=False),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("added_by", sa.String(), nullable=True),
        sa.Column("removed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("removed_by", sa.String(), nullable=True),
        sa.Column("remove_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["lot_id"], ["inventory_lot.id"]),
        sa.ForeignKeyConstraint(["lpn_id"], ["lpn_container.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_id", "lpn_id", "added_at", name="uq_lot_lpn_added"),
    )
    op.create_index("ix_lot_lpn_membership_lot", "lot_lpn_membership", ["lot_id", "removed_at"])
    op.create_index("ix_lot_lpn_membership_lpn", "lot_lpn_membership", ["lpn_id", "removed_at"])

    op.create_table(
        "downstream_vendor",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("vendor_code", sa.String(), nullable=False),
        sa.Column("vendor_name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allowlist_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor_code", name="uq_vendor_code"),
    )
    op.create_index("ix_downstream_vendor_active_allowlist", "downstream_vendor", ["is_active", "allowlist_flag"])

    op.create_table(
        "outbound_shipment",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("shipment_no", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("carrier_name", sa.String(), nullable=True),
        sa.Column("carrier_scac", sa.String(), nullable=True),
        sa.Column("vehicle_plate", sa.String(), nullable=True),
        sa.Column("driver_name", sa.String(), nullable=True),
        sa.Column("appointment_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("seal_number", sa.String(), nullable=True),
        sa.Column("hazmat_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("origin_site_code", sa.String(), nullable=False),
        sa.Column("destination_vendor_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["destination_vendor_id"], ["downstream_vendor.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_no", name="uq_shipment_no"),
    )
    op.create_index("ix_outbound_shipment_status_appt", "outbound_shipment", ["status", "appointment_at"])
    op.create_index("ix_outbound_shipment_vendor", "outbound_shipment", ["destination_vendor_id"])

    op.create_table(
        "shipment_lpn",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("shipment_id", sa.String(), nullable=False),
        sa.Column("lpn_id", sa.String(), nullable=False),
        sa.Column("loaded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("loaded_by", sa.String(), nullable=True),
        sa.Column("unloaded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("unloaded_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["lpn_id"], ["lpn_container.id"]),
        sa.ForeignKeyConstraint(["shipment_id"], ["outbound_shipment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id", "lpn_id", name="uq_shipment_lpn"),
    )
    op.create_index("ix_shipment_lpn_shipment", "shipment_lpn", ["shipment_id"])
    op.create_index("ix_shipment_lpn_lpn", "shipment_lpn", ["lpn_id"])

    op.create_table(
        "vendor_certification",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("vendor_id", sa.String(), nullable=False),
        sa.Column("cert_type", sa.String(), nullable=False),
        sa.Column("cert_number", sa.String(), nullable=True),
        sa.Column("issued_at", sa.String(), nullable=True),
        sa.Column("expires_at", sa.String(), nullable=True),
        sa.Column("effective_from", sa.String(), nullable=False),
        sa.Column("effective_to", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("artifact_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["evidence_artifact.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["downstream_vendor.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendor_cert_vendor", "vendor_certification", ["vendor_id", "cert_type", "is_active"])

    op.create_table(
        "disposition_record",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("lot_id", sa.String(), nullable=False),
        sa.Column("vendor_id", sa.String(), nullable=False),
        sa.Column("shipment_id", sa.String(), nullable=True),
        sa.Column("disposition_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column("final_proof_artifact_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["final_proof_artifact_id"], ["evidence_artifact.id"]),
        sa.ForeignKeyConstraint(["lot_id"], ["inventory_lot.id"]),
        sa.ForeignKeyConstraint(["shipment_id"], ["outbound_shipment.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["downstream_vendor.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_disposition_record_lot_status", "disposition_record", ["lot_id", "status"])
    op.create_index("ix_disposition_record_vendor", "disposition_record", ["vendor_id"])


def downgrade() -> None:
    op.drop_index("ix_disposition_record_vendor", table_name="disposition_record")
    op.drop_index("ix_disposition_record_lot_status", table_name="disposition_record")
    op.drop_table("disposition_record")

    op.drop_index("ix_vendor_cert_vendor", table_name="vendor_certification")
    op.drop_table("vendor_certification")

    op.drop_index("ix_shipment_lpn_lpn", table_name="shipment_lpn")
    op.drop_index("ix_shipment_lpn_shipment", table_name="shipment_lpn")
    op.drop_table("shipment_lpn")

    op.drop_index("ix_outbound_shipment_vendor", table_name="outbound_shipment")
    op.drop_index("ix_outbound_shipment_status_appt", table_name="outbound_shipment")
    op.drop_table("outbound_shipment")

    op.drop_index("ix_downstream_vendor_active_allowlist", table_name="downstream_vendor")
    op.drop_table("downstream_vendor")

    op.drop_index("ix_lot_lpn_membership_lpn", table_name="lot_lpn_membership")
    op.drop_index("ix_lot_lpn_membership_lot", table_name="lot_lpn_membership")
    op.drop_table("lot_lpn_membership")

    op.drop_index("ix_inventory_lot_taxonomy", table_name="inventory_lot")
    op.drop_index("ix_inventory_lot_status", table_name="inventory_lot")
    op.drop_table("inventory_lot")

    op.drop_index("ix_lpn_current_location", table_name="lpn_container")
    op.drop_index("ix_lpn_status", table_name="lpn_container")
    op.drop_table("lpn_container")

    op.drop_index("ix_warehouse_location_site_type", table_name="warehouse_location")
    op.drop_table("warehouse_location")
