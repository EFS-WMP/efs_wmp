"""phase0_i pickup manifest bridge data layer

Revision ID: 0010
Revises: 0009
Create Date: 2026-01-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pickup_manifest",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("manifest_no", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False, server_default="ODOO"),
        sa.Column("odoo_day_route_id", sa.String(), nullable=True),
        sa.Column("odoo_stop_id", sa.String(), nullable=True),
        sa.Column("odoo_pickup_occurrence_id", sa.String(), nullable=True),
        sa.Column("odoo_work_order_id", sa.String(), nullable=True),
        sa.Column("customer_id", sa.String(), nullable=True),
        sa.Column("service_location_id", sa.String(), nullable=True),
        sa.Column("route_snapshot_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("pod_evidence_json", sa.JSON(), server_default=sa.text("'{\"items\": []}'::jsonb"), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_no", name="uq_pickup_manifest_no"),
        sa.UniqueConstraint("source_system", "manifest_fingerprint", name="uq_pickup_manifest_fingerprint"),
        sa.CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','BOUND_TO_BOL','RECEIVED','CLOSED','VOIDED')",
            name="ck_pickup_manifest_status",
        ),
        sa.CheckConstraint(
            "(status <> 'VOIDED') OR (void_reason IS NOT NULL)",
            name="ck_pickup_manifest_void_reason",
        ),
    )
    op.create_index("ix_pickup_manifest_status_submitted", "pickup_manifest", ["status", "submitted_at"])
    op.create_index("ix_pickup_manifest_odoo_route", "pickup_manifest", ["odoo_day_route_id"])
    op.create_index("ix_pickup_manifest_odoo_stop", "pickup_manifest", ["odoo_stop_id"])
    op.create_index("ix_pickup_manifest_corr_id", "pickup_manifest", ["correlation_id"])

    op.create_table(
        "pickup_manifest_state_event",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("pickup_manifest_id", sa.String(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=True),
        sa.Column("to_status", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("payload_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["pickup_manifest_id"], ["pickup_manifest.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pickup_manifest_state_event_manifest",
        "pickup_manifest_state_event",
        ["pickup_manifest_id", "occurred_at"],
    )

    op.create_table(
        "pickup_manifest_integration_attempt",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("pickup_manifest_id", sa.String(), nullable=True),
        sa.Column("source_system", sa.String(), nullable=False, server_default="ODOO"),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("manifest_fingerprint", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("http_status", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["pickup_manifest_id"], ["pickup_manifest.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pickup_manifest_attempt_corr",
        "pickup_manifest_integration_attempt",
        ["correlation_id", "occurred_at"],
    )

    op.create_table(
        "geocode_cache",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("address_hash", sa.String(), nullable=False),
        sa.Column("normalized_address", sa.String(), nullable=False),
        sa.Column("latitude", sa.Numeric(), nullable=False),
        sa.Column("longitude", sa.Numeric(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("confidence", sa.Numeric(), nullable=False),
        sa.Column("result_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("effective_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("address_hash", "effective_from", name="uq_geocode_cache_effective_from"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_geocode_confidence_range"),
    )
    op.create_index("ix_geocode_cache_hash_active", "geocode_cache", ["address_hash", "is_active"])

    with op.batch_alter_table("bol") as batch_op:
        batch_op.add_column(sa.Column("pickup_manifest_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_bol_pickup_manifest",
        "bol",
        "pickup_manifest",
        ["pickup_manifest_id"],
        ["id"],
    )
    op.create_index(
        "uq_bol_pickup_manifest",
        "bol",
        ["pickup_manifest_id"],
        unique=True,
        postgresql_where=sa.text("pickup_manifest_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_bol_pickup_manifest", table_name="bol")
    op.drop_constraint("fk_bol_pickup_manifest", "bol", type_="foreignkey")
    with op.batch_alter_table("bol") as batch_op:
        batch_op.drop_column("pickup_manifest_id")

    op.drop_index("ix_geocode_cache_hash_active", table_name="geocode_cache")
    op.drop_table("geocode_cache")

    op.drop_index("ix_pickup_manifest_attempt_corr", table_name="pickup_manifest_integration_attempt")
    op.drop_table("pickup_manifest_integration_attempt")

    op.drop_index("ix_pickup_manifest_state_event_manifest", table_name="pickup_manifest_state_event")
    op.drop_table("pickup_manifest_state_event")

    op.drop_index("ix_pickup_manifest_corr_id", table_name="pickup_manifest")
    op.drop_index("ix_pickup_manifest_odoo_stop", table_name="pickup_manifest")
    op.drop_index("ix_pickup_manifest_odoo_route", table_name="pickup_manifest")
    op.drop_index("ix_pickup_manifest_status_submitted", table_name="pickup_manifest")
    op.drop_table("pickup_manifest")
