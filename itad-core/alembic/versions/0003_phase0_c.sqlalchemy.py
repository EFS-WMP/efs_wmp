"""phase0_c workflow gates closure

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add requires_* fields to bol
    op.add_column('bol', sa.Column('requires_battery_processing', sa.Boolean(), nullable=False, default=False))
    op.add_column('bol', sa.Column('requires_ewaste_processing', sa.Boolean(), nullable=False, default=False))
    op.add_column('bol', sa.Column('requirements_locked_at', sa.TIMESTAMP(timezone=True), nullable=True))

    # Create bol_stage_gates table
    op.create_table('bol_stage_gates',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('bol_id', sa.String(), nullable=False),
    sa.Column('gate_type', sa.Enum('REQUIREMENTS_CONFIRMED', 'PAPERWORK_VERIFIED', 'STAGING_ZONE_ASSIGNED', 'RECEIVING_ANCHOR_RECORDED', 'WORKSTREAMS_OPENED', 'BOL_CLOSED', name='bolgatetype'), nullable=False),
    sa.Column('occurred_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actor', sa.String(), nullable=True),
    sa.Column('payload_json', sa.JSON(), nullable=True),
    sa.Column('is_void', sa.Boolean(), nullable=False, default=False),
    sa.Column('void_reason', sa.String(), nullable=True),
    sa.Column('voided_gate_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['bol_id'], ['bol.id'], ),
    sa.ForeignKeyConstraint(['voided_gate_id'], ['bol_stage_gates.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bol_stage_gates_bol_id_occurred_at', 'bol_stage_gates', ['bol_id', 'occurred_at'], unique=False)
    op.create_index('idx_bol_stage_gates_bol_id_gate_type', 'bol_stage_gates', ['bol_id', 'gate_type'], unique=False)

    # Create workstreams table
    op.create_table('workstreams',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('bol_id', sa.String(), nullable=False),
    sa.Column('workstream_type', sa.Enum('BATTERY', 'EWASTE', name='workstreamtype'), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'IN_PROGRESS', 'COMPLETED', 'VOIDED', name='workstreamstatus'), nullable=False),
    sa.Column('opened_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('closed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('actor', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['bol_id'], ['bol.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create workstream_stage_gates table
    op.create_table('workstream_stage_gates',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('workstream_id', sa.String(), nullable=False),
    sa.Column('gate_type', sa.Enum('WORKSTREAM_OPENED', 'WORKSTREAM_STARTED', 'WORKSTREAM_COMPLETED', 'WORKSTREAM_VOIDED', name='workstreamgatetype'), nullable=False),
    sa.Column('occurred_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actor', sa.String(), nullable=True),
    sa.Column('payload_json', sa.JSON(), nullable=True),
    sa.Column('is_void', sa.Boolean(), nullable=False, default=False),
    sa.Column('void_reason', sa.String(), nullable=True),
    sa.Column('voided_gate_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['workstream_id'], ['workstreams.id'], ),
    sa.ForeignKeyConstraint(['voided_gate_id'], ['workstream_stage_gates.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Append-only trigger for bol_stage_gates (simplified; full trigger would prevent updates/deletes)
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_bol_stage_gates_update_delete()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'UPDATE' THEN
            RAISE EXCEPTION 'Updates to bol_stage_gates are not allowed';
        ELSIF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Deletes from bol_stage_gates are not allowed';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER bol_stage_gates_append_only
        BEFORE UPDATE OR DELETE ON bol_stage_gates
        FOR EACH ROW EXECUTE FUNCTION prevent_bol_stage_gates_update_delete();
    """)

    # Similar for workstream_stage_gates
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_workstream_stage_gates_update_delete()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'UPDATE' THEN
            RAISE EXCEPTION 'Updates to workstream_stage_gates are not allowed';
        ELSIF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Deletes from workstream_stage_gates are not allowed';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER workstream_stage_gates_append_only
        BEFORE UPDATE OR DELETE ON workstream_stage_gates
        FOR EACH ROW EXECUTE FUNCTION prevent_workstream_stage_gates_update_delete();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS workstream_stage_gates_append_only ON workstream_stage_gates;")
    op.execute("DROP FUNCTION IF EXISTS prevent_workstream_stage_gates_update_delete();")
    op.execute("DROP TRIGGER IF EXISTS bol_stage_gates_append_only ON bol_stage_gates;")
    op.execute("DROP FUNCTION IF EXISTS prevent_bol_stage_gates_update_delete();")

    # Drop tables
    op.drop_table('workstream_stage_gates')
    op.drop_table('workstreams')
    op.drop_table('bol_stage_gates')

    # Drop columns from bol
    op.drop_column('bol', 'requirements_locked_at')
    op.drop_column('bol', 'requires_ewaste_processing')
    op.drop_column('bol', 'requires_battery_processing')
