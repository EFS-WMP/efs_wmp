"""phase0_e taxonomy and processing domains

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "taxonomy_type",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("group_code", sa.String(), nullable=False),
        sa.Column("type_code", sa.String(), nullable=False),
        sa.Column("type_name", sa.String(), nullable=False),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("effective_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_code",
            "type_code",
            "effective_from",
            name="uq_taxonomy_type_group_code_type_code_effective_from",
        ),
    )
    op.create_index("ix_taxonomy_type_group_code", "taxonomy_type", ["group_code"])
    op.create_index("ix_taxonomy_type_type_code", "taxonomy_type", ["type_code"])
    op.create_index("ix_taxonomy_type_is_active", "taxonomy_type", ["is_active"])
    op.create_index("ix_taxonomy_type_effective_from", "taxonomy_type", ["effective_from"])
    op.create_index("ix_taxonomy_type_effective_to", "taxonomy_type", ["effective_to"])

    op.create_table(
        "taxonomy_item",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("taxonomy_type_id", sa.String(), nullable=False),
        sa.Column("variant_code", sa.String(), nullable=False),
        sa.Column("variant_name", sa.String(), nullable=False),
        sa.Column("sb20_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hazard_class", sa.String(), nullable=True),
        sa.Column("un_number", sa.String(), nullable=True),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("effective_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["taxonomy_type_id"], ["taxonomy_type.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "taxonomy_type_id",
            "variant_code",
            "effective_from",
            name="uq_taxonomy_item_type_variant_effective_from",
        ),
    )
    op.create_index("ix_taxonomy_item_type_id", "taxonomy_item", ["taxonomy_type_id"])
    op.create_index("ix_taxonomy_item_variant_code", "taxonomy_item", ["variant_code"])
    op.create_index("ix_taxonomy_item_sb20_flag", "taxonomy_item", ["sb20_flag"])
    op.create_index("ix_taxonomy_item_effective_from", "taxonomy_item", ["effective_from"])
    op.create_index("ix_taxonomy_item_effective_to", "taxonomy_item", ["effective_to"])

    op.create_table(
        "taxonomy_change_log",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taxonomy_change_entity", "taxonomy_change_log", ["entity_type", "entity_id"])
    op.create_index("ix_taxonomy_change_occurred_at", "taxonomy_change_log", ["occurred_at"])

    op.create_table(
        "battery_processing_session",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("bol_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("headcount", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bol_id"], ["bol.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_battery_processing_session_bol_id", "battery_processing_session", ["bol_id"])

    op.create_table(
        "battery_processing_line",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("taxonomy_item_id", sa.String(), nullable=False),
        sa.Column("weight_lbs", sa.Numeric(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("contamination_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("contamination_taxonomy_item_id", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("weight_lbs >= 0", name="ck_battery_line_weight_nonnegative"),
        sa.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_battery_line_quantity_positive"),
        sa.ForeignKeyConstraint(["session_id"], ["battery_processing_session.id"]),
        sa.ForeignKeyConstraint(["taxonomy_item_id"], ["taxonomy_item.id"]),
        sa.ForeignKeyConstraint(["contamination_taxonomy_item_id"], ["taxonomy_item.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_battery_processing_line_session_id", "battery_processing_line", ["session_id"])
    op.create_index("ix_battery_processing_line_taxonomy_item_id", "battery_processing_line", ["taxonomy_item_id"])
    op.create_index(
        "ix_battery_processing_line_contamination_taxonomy_item_id",
        "battery_processing_line",
        ["contamination_taxonomy_item_id"],
    )

    op.create_table(
        "ewaste_processing_session",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("bol_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("headcount", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("headcount > 0", name="ck_ewaste_session_headcount_positive"),
        sa.ForeignKeyConstraint(["bol_id"], ["bol.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ewaste_processing_session_bol_id", "ewaste_processing_session", ["bol_id"])

    op.create_table(
        "ewaste_processing_line",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("taxonomy_item_id", sa.String(), nullable=False),
        sa.Column("weight_lbs", sa.Numeric(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("weight_lbs >= 0", name="ck_ewaste_line_weight_nonnegative"),
        sa.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_ewaste_line_quantity_positive"),
        sa.ForeignKeyConstraint(["session_id"], ["ewaste_processing_session.id"]),
        sa.ForeignKeyConstraint(["taxonomy_item_id"], ["taxonomy_item.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ewaste_processing_line_session_id", "ewaste_processing_line", ["session_id"])
    op.create_index("ix_ewaste_processing_line_taxonomy_item_id", "ewaste_processing_line", ["taxonomy_item_id"])


def downgrade() -> None:
    op.drop_index("ix_ewaste_processing_line_taxonomy_item_id", table_name="ewaste_processing_line")
    op.drop_index("ix_ewaste_processing_line_session_id", table_name="ewaste_processing_line")
    op.drop_table("ewaste_processing_line")

    op.drop_index("ix_ewaste_processing_session_bol_id", table_name="ewaste_processing_session")
    op.drop_table("ewaste_processing_session")

    op.drop_index("ix_battery_processing_line_contamination_taxonomy_item_id", table_name="battery_processing_line")
    op.drop_index("ix_battery_processing_line_taxonomy_item_id", table_name="battery_processing_line")
    op.drop_index("ix_battery_processing_line_session_id", table_name="battery_processing_line")
    op.drop_table("battery_processing_line")

    op.drop_index("ix_battery_processing_session_bol_id", table_name="battery_processing_session")
    op.drop_table("battery_processing_session")

    op.drop_index("ix_taxonomy_change_occurred_at", table_name="taxonomy_change_log")
    op.drop_index("ix_taxonomy_change_entity", table_name="taxonomy_change_log")
    op.drop_table("taxonomy_change_log")

    op.drop_index("ix_taxonomy_item_effective_to", table_name="taxonomy_item")
    op.drop_index("ix_taxonomy_item_effective_from", table_name="taxonomy_item")
    op.drop_index("ix_taxonomy_item_sb20_flag", table_name="taxonomy_item")
    op.drop_index("ix_taxonomy_item_variant_code", table_name="taxonomy_item")
    op.drop_index("ix_taxonomy_item_type_id", table_name="taxonomy_item")
    op.drop_table("taxonomy_item")

    op.drop_index("ix_taxonomy_type_effective_to", table_name="taxonomy_type")
    op.drop_index("ix_taxonomy_type_effective_from", table_name="taxonomy_type")
    op.drop_index("ix_taxonomy_type_is_active", table_name="taxonomy_type")
    op.drop_index("ix_taxonomy_type_type_code", table_name="taxonomy_type")
    op.drop_index("ix_taxonomy_type_group_code", table_name="taxonomy_type")
    op.drop_table("taxonomy_type")
