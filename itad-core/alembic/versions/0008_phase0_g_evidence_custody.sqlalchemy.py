"""phase0_g evidence and custody data layer

Revision ID: 0008
Revises: 0007
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_artifact",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("sha256_hex", sa.String(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("storage_provider", sa.String(), nullable=False),
        sa.Column("storage_ref", sa.String(), nullable=False),
        sa.Column("storage_version", sa.String(), nullable=True),
        sa.Column("retention_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("visibility", sa.String(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sha256_hex",
            "storage_provider",
            "storage_ref",
            name="uq_artifact_content_pointer",
        ),
        sa.CheckConstraint("byte_size >= 0", name="ck_artifact_byte_size_nonnegative"),
        sa.CheckConstraint("sha256_hex ~ '^[0-9a-f]{64}$'", name="ck_artifact_sha256_format"),
    )
    op.create_index("ix_evidence_artifact_type_created", "evidence_artifact", ["artifact_type", "created_at"])
    op.create_index("ix_evidence_artifact_sha", "evidence_artifact", ["sha256_hex"])

    op.create_table(
        "artifact_link",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("link_role", sa.String(), nullable=False),
        sa.Column("visibility_override", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["evidence_artifact.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "artifact_id",
            "entity_type",
            "entity_id",
            "link_role",
            name="uq_artifact_link_unique",
        ),
    )
    op.create_index("ix_artifact_link_entity", "artifact_link", ["entity_type", "entity_id"])

    op.create_table(
        "custody_event",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("from_location_id", sa.String(), nullable=True),
        sa.Column("to_location_id", sa.String(), nullable=True),
        sa.Column("from_location_code", sa.String(), nullable=True),
        sa.Column("to_location_code", sa.String(), nullable=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("supersedes_event_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custody_event_entity", "custody_event", ["entity_type", "entity_id", "occurred_at"])
    op.create_index("ix_custody_event_event_type", "custody_event", ["event_type", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_custody_event_event_type", table_name="custody_event")
    op.drop_index("ix_custody_event_entity", table_name="custody_event")
    op.drop_table("custody_event")

    op.drop_index("ix_artifact_link_entity", table_name="artifact_link")
    op.drop_table("artifact_link")

    op.drop_index("ix_evidence_artifact_sha", table_name="evidence_artifact")
    op.drop_index("ix_evidence_artifact_type_created", table_name="evidence_artifact")
    op.drop_table("evidence_artifact")
