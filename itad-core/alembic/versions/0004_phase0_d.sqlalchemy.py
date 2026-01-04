"""phase0_d receiving anchor immutable

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alter existing enum columns to strings using raw SQL
    op.execute("ALTER TABLE bol ALTER COLUMN source_type TYPE VARCHAR USING source_type::VARCHAR")
    op.execute("ALTER TABLE bol ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")
    op.execute("ALTER TABLE bol_stage_gates ALTER COLUMN gate_type TYPE VARCHAR USING gate_type::VARCHAR")
    op.execute("ALTER TABLE workstreams ALTER COLUMN workstream_type TYPE VARCHAR USING workstream_type::VARCHAR")
    op.execute("ALTER TABLE workstreams ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR")
    op.execute("ALTER TABLE workstream_stage_gates ALTER COLUMN gate_type TYPE VARCHAR USING gate_type::VARCHAR")

    # Add required fields to receiving_weight_record_v3
    op.add_column('receiving_weight_record_v3', sa.Column('material_received_as', sa.String(), nullable=False))
    op.add_column('receiving_weight_record_v3', sa.Column('weight_unit', sa.String(), nullable=False, default='LBS'))
    op.add_column('receiving_weight_record_v3', sa.Column('receiver_signature_json', sa.JSON(), nullable=False))
    op.add_column('receiving_weight_record_v3', sa.Column('tare_source', sa.String(), nullable=False))
    op.add_column('receiving_weight_record_v3', sa.Column('tare_profile_snapshot_json', sa.JSON(), nullable=True))
    op.add_column('receiving_weight_record_v3', sa.Column('tare_instance_snapshot_json', sa.JSON(), nullable=True))
    op.add_column('receiving_weight_record_v3', sa.Column('declared_gross_weight', sa.Numeric(), nullable=True))
    op.add_column('receiving_weight_record_v3', sa.Column('declared_tare_weight', sa.Numeric(), nullable=True))
    op.add_column('receiving_weight_record_v3', sa.Column('declared_net_weight', sa.Numeric(), nullable=True))
    op.add_column('receiving_weight_record_v3', sa.Column('declared_weight_source', sa.String(), nullable=True))
    op.add_column('receiving_weight_record_v3', sa.Column('reissue_of_id', sa.String(), nullable=True))

    # Create receiving_record_voids table
    op.create_table('receiving_record_voids',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('receiving_record_id', sa.String(), nullable=False),
    sa.Column('void_reason', sa.String(), nullable=False),
    sa.Column('voided_by', sa.String(), nullable=False),
    sa.Column('voided_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['receiving_record_id'], ['receiving_weight_record_v3.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Add FK for reissue_of_id
    op.create_foreign_key('fk_receiving_reissue_of', 'receiving_weight_record_v3', 'receiving_weight_record_v3', ['reissue_of_id'], ['id'])

    # DB check for tare_source snapshots
    op.execute("""
    ALTER TABLE receiving_weight_record_v3
    ADD CONSTRAINT check_tare_snapshot
    CHECK (
        (tare_source NOT LIKE '%SNAPSHOT%' OR tare_source LIKE '%SNAPSHOT%') AND
        (tare_source NOT LIKE '%PROFILE%' OR tare_profile_snapshot_json IS NOT NULL) AND
        (tare_source NOT LIKE '%INSTANCE%' OR tare_instance_snapshot_json IS NOT NULL)
    );
    """)


def downgrade() -> None:
    # Drop check constraint
    op.execute("ALTER TABLE receiving_weight_record_v3 DROP CONSTRAINT IF EXISTS check_tare_snapshot;")

    # Drop FK
    op.drop_constraint('fk_receiving_reissue_of', 'receiving_weight_record_v3', type_='foreignkey')

    # Drop table
    op.drop_table('receiving_record_voids')

    # Drop columns
    op.drop_column('receiving_weight_record_v3', 'reissue_of_id')
    op.drop_column('receiving_weight_record_v3', 'declared_weight_source')
    op.drop_column('receiving_weight_record_v3', 'declared_net_weight')
    op.drop_column('receiving_weight_record_v3', 'declared_tare_weight')
    op.drop_column('receiving_weight_record_v3', 'declared_gross_weight')
    op.drop_column('receiving_weight_record_v3', 'tare_instance_snapshot_json')
    op.drop_column('receiving_weight_record_v3', 'tare_profile_snapshot_json')
    op.drop_column('receiving_weight_record_v3', 'tare_source')
    op.drop_column('receiving_weight_record_v3', 'receiver_signature_json')
    op.drop_column('receiving_weight_record_v3', 'weight_unit')
    op.drop_column('receiving_weight_record_v3', 'material_received_as')
