# File: itad_core/models/itad_material_type_cache.py

from odoo import api, fields, models
from odoo.exceptions import UserError


class ItadMaterialTypeCache(models.Model):
    """
    Material Type Cache - Read-Only Local Cache of ITAD Core Taxonomy
    
    Phase 2.3: This model stores a read-only copy of material taxonomy from
    ITAD Core (the System of Record). Users CANNOT create/edit/delete records
    directly. Only the sync engine (via context {'itad_sync': True}) can modify.
    """
    _name = "itad.material.type.cache"
    _description = "Material Type Cache (from ITAD Core)"
    _order = "code"
    
    # Primary keys from ITAD Core
    itad_core_uuid = fields.Char(
        string="ITAD Core UUID",
        required=True,
        index=True,
        readonly=True,
        help="Stable UUID from ITAD Core (primary sync key)",
    )
    
    code = fields.Char(
        string="Material Code",
        required=True,
        index=True,
        readonly=True,
        help="Unique material code (e.g., BAT-LI-001)",
    )
    
    # Core taxonomy fields
    name = fields.Char(
        string="Material Name",
        required=True,
        readonly=True,
    )
    
    stream = fields.Char(
        string="Stream",
        index=True,
        readonly=True,
        help="Material stream category (e.g., batteries, electronics)",
    )
    
    hazard_class = fields.Char(
        string="Hazard Class",
        readonly=True,
        help="DOT hazard class if applicable (e.g., 'Class 9')",
    )
    
    default_action = fields.Char(
        string="Default Action",
        readonly=True,
        help="Default processing action (e.g., recycle, dispose)",
    )
    
    # Validation flags
    requires_photo = fields.Boolean(
        string="Requires Photo",
        default=False,
        readonly=True,
        help="If true, receiving wizard must have attachment(s)",
    )
    
    requires_weight = fields.Boolean(
        string="Requires Weight",
        default=False,
        readonly=True,
        help="If true, receiving wizard must provide weight",
    )
    
    # Active flag (maps to is_active from ITAD Core)
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Inactive records are hidden from wizard dropdowns but retained in cache",
    )
    
    # Phase 2.4a Enhancement: Pricing State
    pricing_state = fields.Selection(
        [
            ("priced", "Priced"),
            ("unpriced", "Unpriced"),
            ("contract", "Contract"),
            ("deprecated", "Deprecated"),
        ],
        string="Pricing State",
        default="unpriced",
        readonly=True,
        help="Pricing policy: priced (billing required), unpriced, contract, deprecated",
    )
    
    # Sync metadata
    source_updated_at = fields.Datetime(
        string="Source Updated At",
        readonly=True,
        help="Timestamp from ITAD Core when this record was last updated there",
    )
    
    last_synced_at = fields.Datetime(
        string="Last Synced At",
        readonly=True,
        help="Timestamp when this record was last synced from ITAD Core",
    )
    
    source_hash = fields.Char(
        string="Source Hash",
        readonly=True,
        help="Hash of source fields for change detection (optional optimization)",
    )
    
    # Phase 2.4a: Billing Metadata Fields
    default_price = fields.Float(
        string="Default Price",
        digits=(12, 4),
        readonly=True,
        help="Default price for billing",
    )
    
    basis_of_charge = fields.Selection(
        [
            ("per_lb", "Per Lb"),
            ("per_kg", "Per Kg"),
            ("per_unit", "Per Unit"),
            ("flat_fee", "Flat Fee"),
        ],
        string="Basis of Charge",
        readonly=True,
        help="How pricing is calculated",
    )
    
    gl_account_code = fields.Char(
        string="GL Account Code",
        size=64,
        readonly=True,
        help="General ledger account code for accounting integration",
    )
    
    _sql_constraints = [
        (
            "unique_itad_core_uuid",
            "UNIQUE(itad_core_uuid)",
            "ITAD Core UUID must be unique",
        ),
        (
            "unique_code",
            "UNIQUE(code)",
            "Material code must be unique",
        ),
    ]
    
    @api.model
    def create(self, vals):
        """
        Override create to enforce read-only cache unless integration group OR superuser.
        
        SECURITY: Context flags like {'itad_sync': True} are NOT sufficient for permission.
        Only users with itad_core.group_itad_integration or superuser can write.
        Sync engine must call with sudo() AND ensure user has integration group.
        """
        if not self._check_integration_permission():
            raise UserError(
                "Material types are read-only cache synchronized from ITAD Core. "
                "They cannot be manually created. Use 'Sync Now' button to refresh taxonomy."
            )
        return super().create(vals)
    
    def write(self, vals):
        """
        Override write to enforce read-only cache unless integration group OR superuser.
        
        SECURITY: Context flags like {'itad_sync': True} are NOT sufficient for permission.
        Only users with itad_core.group_itad_integration or superuser can write.
        """
        if not self._check_integration_permission():
            raise UserError(
                "Material types are read-only cache synchronized from ITAD Core. "
                "They cannot be manually modified. Use 'Sync Now' button to refresh taxonomy."
            )
        return super().write(vals)
    
    def unlink(self):
        """
        Override unlink to enforce read-only cache unless integration group OR superuser.
        
        SECURITY: Records are deactivated, not deleted. Manual deletion is prohibited.
        """
        if not self._check_integration_permission():
            raise UserError(
                "Material types are read-only cache synchronized from ITAD Core. "
                "Records are deactivated, not deleted. Use 'Sync Now' button to refresh taxonomy."
            )
        return super().unlink()
    
    def _check_integration_permission(self):
        """
        Check if current user has permission to modify cache.
        
        Returns True if:
        - User is superuser (env.is_superuser())
        - User has itad_core.group_itad_integration group
        
        Context flags are ignored for security.
        """
        return (
            self.env.is_superuser() or
            self.env.user.has_group('itad_core.group_itad_integration')
        )
