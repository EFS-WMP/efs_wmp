"""phase0_d receiving constraints

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET tare_source = 'CONTAINER_TYPE_PROFILE_SNAPSHOT' "
        "WHERE tare_source = 'PROFILE_SNAPSHOT'"
    )
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET tare_source = 'CONTAINER_INSTANCE_SNAPSHOT' "
        "WHERE tare_source = 'INSTANCE_SNAPSHOT'"
    )
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET tare_source = 'MANUAL_TARE_WITH_APPROVAL' "
        "WHERE tare_source = 'MANUAL'"
    )
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET receiver_signature_json = '{}' "
        "WHERE receiver_signature_json IS NULL"
    )
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET weight_unit = 'LBS' "
        "WHERE weight_unit IS NULL"
    )
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET ddr_status = false "
        "WHERE ddr_status IS NULL"
    )
    op.execute(
        "UPDATE receiving_weight_record_v3 "
        "SET receiver_employee_id = 'UNKNOWN' "
        "WHERE receiver_employee_id IS NULL"
    )

    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN occurred_at TYPE TIMESTAMPTZ "
        "USING occurred_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN quantity TYPE INTEGER "
        "USING quantity::integer"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN receiver_signature_json TYPE JSONB "
        "USING receiver_signature_json::jsonb"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN tare_profile_snapshot_json TYPE JSONB "
        "USING tare_profile_snapshot_json::jsonb"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN tare_instance_snapshot_json TYPE JSONB "
        "USING tare_instance_snapshot_json::jsonb"
    )

    op.alter_column(
        "receiving_weight_record_v3",
        "ddr_status",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    op.alter_column(
        "receiving_weight_record_v3",
        "receiver_employee_id",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "receiving_weight_record_v3",
        "weight_unit",
        existing_type=sa.String(),
        nullable=False,
        server_default=sa.text("'LBS'"),
    )

    op.execute("ALTER TABLE receiving_weight_record_v3 DROP CONSTRAINT IF EXISTS check_tare_snapshot")

    op.create_check_constraint(
        "ck_receiving_quantity_positive",
        "receiving_weight_record_v3",
        "quantity > 0",
    )
    op.create_check_constraint(
        "ck_receiving_gross_weight_nonnegative",
        "receiving_weight_record_v3",
        "gross_weight >= 0",
    )
    op.create_check_constraint(
        "ck_receiving_tare_weight_nonnegative",
        "receiving_weight_record_v3",
        "tare_weight >= 0",
    )
    op.create_check_constraint(
        "ck_receiving_net_weight_nonnegative",
        "receiving_weight_record_v3",
        "net_weight >= 0",
    )
    op.create_check_constraint(
        "ck_receiving_tare_source_allowed",
        "receiving_weight_record_v3",
        "tare_source IN ("
        "'MEASURED_ON_SCALE', "
        "'CONTAINER_INSTANCE_SNAPSHOT', "
        "'CONTAINER_TYPE_PROFILE_SNAPSHOT', "
        "'MANUAL_TARE_WITH_APPROVAL'"
        ")",
    )
    op.create_check_constraint(
        "ck_receiving_tare_snapshot_required",
        "receiving_weight_record_v3",
        "("
        "tare_source != 'CONTAINER_INSTANCE_SNAPSHOT' "
        "OR tare_instance_snapshot_json IS NOT NULL"
        ") AND ("
        "tare_source != 'CONTAINER_TYPE_PROFILE_SNAPSHOT' "
        "OR tare_profile_snapshot_json IS NOT NULL"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_receiving_tare_snapshot_required", "receiving_weight_record_v3", type_="check")
    op.drop_constraint("ck_receiving_tare_source_allowed", "receiving_weight_record_v3", type_="check")
    op.drop_constraint("ck_receiving_net_weight_nonnegative", "receiving_weight_record_v3", type_="check")
    op.drop_constraint("ck_receiving_tare_weight_nonnegative", "receiving_weight_record_v3", type_="check")
    op.drop_constraint("ck_receiving_gross_weight_nonnegative", "receiving_weight_record_v3", type_="check")
    op.drop_constraint("ck_receiving_quantity_positive", "receiving_weight_record_v3", type_="check")

    op.alter_column(
        "receiving_weight_record_v3",
        "weight_unit",
        existing_type=sa.String(),
        nullable=False,
        server_default=None,
    )
    op.alter_column(
        "receiving_weight_record_v3",
        "receiver_employee_id",
        existing_type=sa.String(),
        nullable=True,
    )
    op.alter_column(
        "receiving_weight_record_v3",
        "ddr_status",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )

    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN tare_instance_snapshot_json TYPE JSON "
        "USING tare_instance_snapshot_json::json"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN tare_profile_snapshot_json TYPE JSON "
        "USING tare_profile_snapshot_json::json"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN receiver_signature_json TYPE JSON "
        "USING receiver_signature_json::json"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN quantity TYPE NUMERIC "
        "USING quantity::numeric"
    )
    op.execute(
        "ALTER TABLE receiving_weight_record_v3 "
        "ALTER COLUMN occurred_at TYPE TIMESTAMP "
        "USING occurred_at AT TIME ZONE 'UTC'"
    )

    op.execute(
        """
        ALTER TABLE receiving_weight_record_v3
        ADD CONSTRAINT check_tare_snapshot
        CHECK (
            (tare_source NOT LIKE '%SNAPSHOT%' OR tare_source LIKE '%SNAPSHOT%') AND
            (tare_source NOT LIKE '%PROFILE%' OR tare_profile_snapshot_json IS NOT NULL) AND
            (tare_source NOT LIKE '%INSTANCE%' OR tare_instance_snapshot_json IS NOT NULL)
        );
        """
    )
