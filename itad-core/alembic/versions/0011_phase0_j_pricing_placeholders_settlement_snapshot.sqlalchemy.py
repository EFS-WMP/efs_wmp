"""Phase 0.J pricing placeholders and settlement snapshot"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pricing_external_ref",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ref_type", sa.String(), nullable=False),
        sa.Column("odoo_record_model", sa.String(), nullable=False),
        sa.Column("odoo_record_id", sa.String(), nullable=False),
        sa.Column("odoo_version", sa.String(), nullable=True),
        sa.Column("ref_hash_sha256", sa.String(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("ref_hash_sha256 ~ '^[0-9a-f]{64}$'", name="ck_pricing_external_ref_hash_format"),
    )
    op.create_index(
        "idx_pricing_external_ref_customer_type_active",
        "pricing_external_ref",
        ["customer_id", "ref_type", "is_active"],
        unique=False,
    )
    op.create_index(
        "uq_pricing_external_ref_unique",
        "pricing_external_ref",
        ["ref_type", "odoo_record_model", "odoo_record_id", "effective_from"],
        unique=True,
    )

    op.create_table(
        "settlement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bol_id", sa.String(), sa.ForeignKey("bol.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("idx_settlement_bol_status", "settlement", ["bol_id", "status"], unique=False)

    op.create_table(
        "settlement_pricing_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("settlement.id"), nullable=False),
        sa.Column("snapshot_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("customer_pricing_profile_ref_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_external_ref.id"), nullable=True),
        sa.Column("service_catalog_ref_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_external_ref.id"), nullable=True),
        sa.Column("rate_card_ref_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_external_ref.id"), nullable=True),
        sa.Column("tier_ruleset_ref_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_external_ref.id"), nullable=True),
        sa.Column("pricing_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("basis_of_charge_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("computed_lines_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text('\'{"lines": []}\'::jsonb')),
        sa.Column("snapshot_hash_sha256", sa.String(), nullable=False),
        sa.CheckConstraint("snapshot_hash_sha256 ~ '^[0-9a-f]{64}$'", name="ck_settlement_snapshot_hash_format"),
    )
    op.create_index("uq_settlement_snapshot_no", "settlement_pricing_snapshot", ["settlement_id", "snapshot_no"], unique=True)
    op.create_index("idx_settlement_snapshot_created", "settlement_pricing_snapshot", ["settlement_id", "created_at"], unique=False)

    op.create_table(
        "settlement_adjustment_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("settlement.id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("reason_text", sa.String(), nullable=False),
        sa.Column("approver", sa.String(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("related_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("settlement_pricing_snapshot.id"), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_settlement_adjustment_currency"),
    )
    op.create_index("idx_settlement_adjustment", "settlement_adjustment_event", ["settlement_id", "occurred_at"], unique=False)


def downgrade():
    op.drop_index("idx_settlement_adjustment", table_name="settlement_adjustment_event")
    op.drop_table("settlement_adjustment_event")
    op.drop_index("idx_settlement_snapshot_created", table_name="settlement_pricing_snapshot")
    op.drop_index("uq_settlement_snapshot_no", table_name="settlement_pricing_snapshot")
    op.drop_table("settlement_pricing_snapshot")
    op.drop_index("idx_settlement_bol_status", table_name="settlement")
    op.drop_table("settlement")
    op.drop_index("uq_pricing_external_ref_unique", table_name="pricing_external_ref")
    op.drop_index("idx_pricing_external_ref_customer_type_active", table_name="pricing_external_ref")
    op.drop_table("pricing_external_ref")
