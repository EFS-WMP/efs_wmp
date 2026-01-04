"""phase0_b identifiers versioning

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence for BOL numbers
    op.execute("CREATE SEQUENCE bol_number_seq START 1")

    # Add new columns to bol
    op.add_column('bol', sa.Column('requirement_profile_version', sa.String(), nullable=True))
    op.add_column('bol', sa.Column('requirement_profile_effective_from', sa.TIMESTAMP(timezone=True), nullable=True))

    # Drop old external_id_map table
    op.drop_index('idx_external_routific_job', table_name='external_id_map')
    op.drop_index('idx_external_odoo_work_order', table_name='external_id_map')
    op.drop_index('idx_external_odoo_day_route', table_name='external_id_map')
    op.drop_index('idx_external_odoo_customer', table_name='external_id_map')
    op.drop_table('external_id_map')

    # Create new external_id_map table
    op.create_table('external_id_map',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('system', sa.String(), nullable=False),
    sa.Column('entity_type', sa.String(), nullable=False),
    sa.Column('external_id', sa.String(), nullable=False),
    sa.Column('itad_entity_id', sa.String(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('system', 'entity_type', 'external_id', name='uq_external_id_map_system_entity_external')
    )
    op.create_index('idx_external_system_entity', 'external_id_map', ['system', 'entity_type'], unique=False)
    op.create_index('idx_external_itad_entity', 'external_id_map', ['itad_entity_id'], unique=False)


def downgrade() -> None:
    # Drop new external_id_map
    op.drop_index('idx_external_itad_entity', table_name='external_id_map')
    op.drop_index('idx_external_system_entity', table_name='external_id_map')
    op.drop_table('external_id_map')

    # Recreate old external_id_map
    op.create_table('external_id_map',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('odoo_customer_id', sa.String(), nullable=True),
    sa.Column('odoo_location_id', sa.String(), nullable=True),
    sa.Column('odoo_work_order_id', sa.String(), nullable=True),
    sa.Column('odoo_day_route_id', sa.String(), nullable=True),
    sa.Column('routific_job_id', sa.String(), nullable=True),
    sa.Column('routific_vehicle_id', sa.String(), nullable=True),
    sa.Column('entity_type', sa.String(), nullable=False),
    sa.Column('itad_entity_id', sa.String(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_external_odoo_customer', 'external_id_map', ['odoo_customer_id'], unique=False)
    op.create_index('idx_external_odoo_day_route', 'external_id_map', ['odoo_day_route_id'], unique=False)
    op.create_index('idx_external_odoo_work_order', 'external_id_map', ['odoo_work_order_id'], unique=False)
    op.create_index('idx_external_routific_job', 'external_id_map', ['routific_job_id'], unique=False)

    # Drop new columns from bol
    op.drop_column('bol', 'requirement_profile_effective_from')
    op.drop_column('bol', 'requirement_profile_version')

    # Drop sequence
    op.execute("DROP SEQUENCE bol_number_seq")
