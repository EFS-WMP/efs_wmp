"""
Phase 2.4a: Add billing metadata fields to material_types

Adds:
- pricing_state: VARCHAR(20) enum (priced, unpriced, contract, deprecated) - default unpriced
- default_price: NUMERIC(12,4) for base pricing
- basis_of_charge: VARCHAR(20) with enum check (per_lb, per_kg, per_unit, flat_fee)
- gl_account_code: VARCHAR(64) for accounting integration

Constraints:
- ck_pricing_state_enum: pricing_state must be one of allowed values
- ck_priced_requires_billing: when pricing_state='priced', default_price AND basis_of_charge required
- ck_basis_of_charge_enum: basis_of_charge must be one of allowed values or null
- ck_default_price_positive: default_price must be >= 0 or null
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011_phase0_j_pricing_placeholders_settlement_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add billing metadata columns and constraints to material_types."""
    
    # Add pricing_state column (with default for existing rows)
    op.add_column(
        "material_types",
        sa.Column("pricing_state", sa.String(20), nullable=False, server_default="unpriced"),
    )
    
    # Add billing columns
    op.add_column(
        "material_types",
        sa.Column("default_price", sa.Numeric(12, 4), nullable=True),
    )
    op.add_column(
        "material_types",
        sa.Column("basis_of_charge", sa.String(20), nullable=True),
    )
    op.add_column(
        "material_types",
        sa.Column("gl_account_code", sa.String(64), nullable=True),
    )
    
    # Add check constraints for validation
    op.create_check_constraint(
        "ck_pricing_state_enum",
        "material_types",
        "pricing_state IN ('priced', 'unpriced', 'contract', 'deprecated')",
    )
    
    op.create_check_constraint(
        "ck_priced_requires_billing",
        "material_types",
        "(pricing_state != 'priced') OR (default_price IS NOT NULL AND basis_of_charge IS NOT NULL)",
    )
    
    op.create_check_constraint(
        "ck_basis_of_charge_enum",
        "material_types",
        "basis_of_charge IN ('per_lb', 'per_kg', 'per_unit', 'flat_fee') OR basis_of_charge IS NULL",
    )
    
    op.create_check_constraint(
        "ck_default_price_positive",
        "material_types",
        "default_price >= 0 OR default_price IS NULL",
    )


def downgrade() -> None:
    """Remove billing metadata columns and constraints from material_types."""
    
    # Drop constraints first
    op.drop_constraint("ck_default_price_positive", "material_types", type_="check")
    op.drop_constraint("ck_basis_of_charge_enum", "material_types", type_="check")
    op.drop_constraint("ck_priced_requires_billing", "material_types", type_="check")
    op.drop_constraint("ck_pricing_state_enum", "material_types", type_="check")
    
    # Drop columns
    op.drop_column("material_types", "gl_account_code")
    op.drop_column("material_types", "basis_of_charge")
    op.drop_column("material_types", "default_price")
    op.drop_column("material_types", "pricing_state")

