"""
Phase 2.4: Material Type Model

SQLAlchemy model for material types (authoritative taxonomy).
Includes billing metadata fields (Phase 2.4a).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, String, DateTime, Index, Numeric, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# Phase 2.4: Centralized enum values for basis_of_charge
# These values are the single source of truth for validation
BASIS_OF_CHARGE_VALUES = ("per_lb", "per_kg", "per_unit", "flat_fee")

# Phase 2.4 Enhancement: Pricing state enum
# Lifecycle semantics:
# - priced: billing fields required (default_price, basis_of_charge) - standard billable material
# - unpriced: billing fields optional (allow nulls) - not yet configured for billing
# - contract: pricing exists in customer contract, NOT in material type
#             default_price may be NULL by design (lookup happens at invoice time)
# - deprecated: legacy material, still retained for historical reporting
#               RECOMMENDATION: set is_active=False in combination to hide from dropdowns
#               but keep in cache for historical lookups
PRICING_STATE_VALUES = ("priced", "unpriced", "contract", "deprecated")


class MaterialType(Base):
    """
    Material Type - Authoritative taxonomy for material classification.
    
    ITAD Core is SoR for this data. Odoo maintains read-only cache.
    
    Phase 2.4: Added billing metadata fields:
    - pricing_state: Pricing policy (priced|unpriced|contract|deprecated)
    - default_price: Base price for billing (NUMERIC(12,4))
    - basis_of_charge: How pricing is calculated (per_lb, per_kg, per_unit, flat_fee)
    - gl_account_code: General ledger account code for accounting integration
    
    Validation:
    - If pricing_state = 'priced': default_price AND basis_of_charge are REQUIRED
    - Otherwise: default_price and basis_of_charge may be NULL
    """
    __tablename__ = "material_types"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    
    stream: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    hazard_class: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    default_action: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    requires_photo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    
    requires_weight: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )
    
    # Phase 2.4a Enhancement: Pricing State
    pricing_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unpriced",
        server_default="unpriced",
        doc="Pricing policy: priced (billing required), unpriced, contract, deprecated",
    )
    
    # Phase 2.4a: Billing Metadata Fields
    
    default_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        doc="Default price for billing. Required if pricing_state='priced'.",
    )
    
    basis_of_charge: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="How pricing is calculated. Required if pricing_state='priced'.",
    )
    
    gl_account_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="General ledger account code for accounting integration",
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )
    
    __table_args__ = (
        Index("ix_material_types_stream_active", "stream", "is_active"),
        Index("ix_material_types_updated_at_desc", "updated_at", postgresql_ops={"updated_at": "DESC"}),
        # Phase 2.4 Enhancement: pricing_state enum validation
        CheckConstraint(
            "pricing_state IN ('priced', 'unpriced', 'contract', 'deprecated')",
            name="ck_pricing_state_enum",
        ),
        # Phase 2.4 Enhancement: Conditional billing requirement
        # When pricing_state = 'priced', both default_price and basis_of_charge must be set
        CheckConstraint(
            "(pricing_state != 'priced') OR (default_price IS NOT NULL AND basis_of_charge IS NOT NULL)",
            name="ck_priced_requires_billing",
        ),
        # Phase 2.4: basis_of_charge enum validation
        CheckConstraint(
            "basis_of_charge IN ('per_lb', 'per_kg', 'per_unit', 'flat_fee') OR basis_of_charge IS NULL",
            name="ck_basis_of_charge_enum",
        ),
        # Phase 2.4: default_price must be non-negative
        CheckConstraint(
            "default_price >= 0 OR default_price IS NULL",
            name="ck_default_price_positive",
        ),
    )

