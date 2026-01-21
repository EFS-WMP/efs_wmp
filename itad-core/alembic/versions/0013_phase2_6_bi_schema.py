"""Phase 2.6: BI Schema and Canonical Reporting Views

Revision ID: 0013
Revises: 0012
Create Date: 2026-01-18

Creates the bi schema with versioned, read-only reporting views:
- bi.material_types_v1
- bi.receiving_records_v1
- bi.receiving_kpis_daily_v1
- bi.dataset_freshness (table for monitoring)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers
revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bi schema
    op.execute("CREATE SCHEMA IF NOT EXISTS bi")
    
    # bi.material_types_v1 view
    op.execute("""
        CREATE OR REPLACE VIEW bi.material_types_v1 AS
        SELECT
            id AS material_type_id,
            code,
            name,
            stream,
            hazard_class,
            default_action,
            requires_photo,
            requires_weight,
            is_active,
            pricing_state,
            default_price,
            basis_of_charge,
            gl_account_code,
            updated_at
        FROM material_types
    """)
    
    # bi.receiving_records_v1 view
    # Joins to material_types for denormalized stream
    op.execute("""
        CREATE OR REPLACE VIEW bi.receiving_records_v1 AS
        SELECT
            r.id AS receiving_record_id,
            r.occurred_at,
            r.bol_id,
            r.material_received_as AS material_type_code,
            COALESCE(m.stream, 'unknown') AS material_stream,
            r.quantity,
            r.gross_weight,
            r.tare_weight,
            r.net_weight,
            r.weight_unit,
            r.receiver_employee_id,
            r.is_void,
            r.created_at
        FROM receiving_weight_record_v3 r
        LEFT JOIN material_types m ON r.material_received_as = m.code
    """)
    
    # bi.receiving_kpis_daily_v1 view (daily aggregates)
    op.execute("""
        CREATE OR REPLACE VIEW bi.receiving_kpis_daily_v1 AS
        SELECT
            DATE(occurred_at AT TIME ZONE 'UTC') AS report_date,
            COALESCE(m.stream, 'unknown') AS stream,
            r.material_received_as AS material_type_code,
            SUM(r.net_weight) AS total_net_weight,
            COUNT(*) AS total_receipts_count
        FROM receiving_weight_record_v3 r
        LEFT JOIN material_types m ON r.material_received_as = m.code
        WHERE r.is_void = false
        GROUP BY DATE(r.occurred_at AT TIME ZONE 'UTC'), m.stream, r.material_received_as
    """)
    
    # bi.dataset_freshness table for monitoring
    op.execute("""
        CREATE TABLE IF NOT EXISTS bi.dataset_freshness (
            id SERIAL PRIMARY KEY,
            dataset_name TEXT NOT NULL,
            dataset_version TEXT NOT NULL,
            computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            max_source_updated_at TIMESTAMP WITH TIME ZONE,
            row_count INTEGER,
            status TEXT DEFAULT 'unknown',
            UNIQUE (dataset_name, dataset_version)
        )
    """)
    
    # Create index on dataset_freshness for quick lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dataset_freshness_name_version
        ON bi.dataset_freshness (dataset_name, dataset_version)
    """)
    
    # Grant read access comment (for documentation)
    # Actual role creation should be done by DBA
    op.execute("""
        COMMENT ON SCHEMA bi IS 
        'Read-only BI reporting schema. Version 1.0. See docs/reporting_contract.md'
    """)


def downgrade() -> None:
    # Drop views and table
    op.execute("DROP VIEW IF EXISTS bi.receiving_kpis_daily_v1")
    op.execute("DROP VIEW IF EXISTS bi.receiving_records_v1")
    op.execute("DROP VIEW IF EXISTS bi.material_types_v1")
    op.execute("DROP TABLE IF EXISTS bi.dataset_freshness")
    
    # Drop schema (only if empty now)
    op.execute("DROP SCHEMA IF EXISTS bi")
