"""phase0_f reconciliation and disputes data layer

Revision ID: 0007
Revises: 0006
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_run",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("bol_id", sa.String(), nullable=False),
        sa.Column("run_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("receiving_total_net_lbs", sa.Numeric(), nullable=False),
        sa.Column("processing_total_lbs", sa.Numeric(), nullable=False),
        sa.Column("variance_lbs", sa.Numeric(), nullable=False),
        sa.Column("variance_pct", sa.Numeric(), nullable=False),
        sa.Column("threshold_pct", sa.Numeric(), nullable=False),
        sa.Column("threshold_lbs", sa.Numeric(), nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("computed_by", sa.String(), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["bol_id"], ["bol.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bol_id", "run_no", name="uq_reconciliation_run_bol_run_no"),
        sa.CheckConstraint("receiving_total_net_lbs >= 0", name="ck_recon_run_receiving_nonnegative"),
        sa.CheckConstraint("processing_total_lbs >= 0", name="ck_recon_run_processing_nonnegative"),
    )
    op.create_index(
        "ix_reconciliation_run_bol_status_computed",
        "reconciliation_run",
        ["bol_id", "status", "computed_at"],
    )

    op.create_table(
        "reconciliation_approval_event",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("reconciliation_run_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("approver", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["reconciliation_run_id"], ["reconciliation_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reconciliation_approval_event_run_decided",
        "reconciliation_approval_event",
        ["reconciliation_run_id", "decided_at"],
    )

    op.create_table(
        "discrepancy_case",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("bol_id", sa.String(), nullable=False),
        sa.Column("case_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("discrepancy_type", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolution_text", sa.String(), nullable=True),
        sa.Column("artifact_refs_json", sa.JSON(), nullable=True),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(), nullable=True),
        sa.Column("void_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["bol_id"], ["bol.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bol_id", "case_no", name="uq_discrepancy_case_bol_case_no"),
        sa.CheckConstraint(
            "("
            "(status IN ('OPEN','IN_DISPUTE') AND resolved_at IS NULL)"
            " OR "
            "(status IN ('RESOLVED','VOIDED'))"
            ")",
            name="ck_discrepancy_state_resolution",
        ),
    )
    op.create_index("ix_discrepancy_case_bol_status", "discrepancy_case", ["bol_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_discrepancy_case_bol_status", table_name="discrepancy_case")
    op.drop_table("discrepancy_case")

    op.drop_index("ix_reconciliation_approval_event_run_decided", table_name="reconciliation_approval_event")
    op.drop_table("reconciliation_approval_event")

    op.drop_index("ix_reconciliation_run_bol_status_computed", table_name="reconciliation_run")
    op.drop_table("reconciliation_run")
