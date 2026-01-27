# File: itad_core/models/itad_taxonomy_sync_state.py

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class ItadTaxonomySyncState(models.Model):
    """
    Taxonomy Sync State - Singleton Model Tracking Sync Status
    
    Phase 2.3: Stores metadata about the last sync run to track health and cursor.
    Should only have one record. Prevents concurrency issues and shows sync status.
    """
    _name = "itad.taxonomy.sync.state"
    _description = "Taxonomy Sync State (Singleton)"
    
    name = fields.Char(
        string="Name",
        default="Material Taxonomy Sync State",
        readonly=True,
    )
    
    # Sync timestamps
    last_success_at = fields.Datetime(
        string="Last Successful Sync",
        readonly=True,
        help="Timestamp of last successful sync from ITAD Core",
    )
    
    last_attempt_at = fields.Datetime(
        string="Last Sync Attempt",
        readonly=True,
        help="Timestamp of last sync attempt (success or failure)",
    )
    
    # Error tracking
    last_error = fields.Text(
        string="Last Error",
        readonly=True,
        help="Error message from last failed sync (cleared on success)",
    )
    
    # Incremental sync cursor
    last_cursor_updated_since = fields.Datetime(
        string="Last Cursor (updated_since)",
        readonly=True,
        help="The max(updated_at) from last sync response - used as cursor for next incremental sync",
    )
    
    # Stats from last run
    stats_last_run = fields.Text(
        string="Stats (Last Run)",
        readonly=True,
        help="JSON-formatted stats: created, updated, deactivated, unchanged counts",
    )
    
    # Break-glass support (Phase 2.3 Security)
    break_glass_reason = fields.Text(
        string="Break-Glass Reason",
        help="Documented reason for enabling break-glass override (required when break-glass is enabled)",
    )
    
    # Phase 2.5: Computed status fields for dashboard
    sync_state = fields.Selection(
        [
            ("ok", "OK"),
            ("warn", "Warning"),
            ("error", "Error"),
        ],
        string="Sync State",
        compute="_compute_sync_state",
        store=False,
    )
    
    stale_age_hours = fields.Float(
        string="Stale Age (hours)",
        compute="_compute_sync_state",
        store=False,
    )
    
    @api.depends("last_success_at", "last_error")
    def _compute_sync_state(self):
        icp = self.env["ir.config_parameter"].sudo()
        max_stale_hours = int(icp.get_param("itad_core.taxonomy.sync.max_stale_hours", "24"))
        
        now = fields.Datetime.now()
        for rec in self:
            if rec.last_success_at:
                delta = now - rec.last_success_at
                rec.stale_age_hours = delta.total_seconds() / 3600
            else:
                rec.stale_age_hours = 9999  # Never synced
            
            if rec.last_error:
                rec.sync_state = "error"
            elif rec.stale_age_hours > max_stale_hours * 2:
                rec.sync_state = "error"
            elif rec.stale_age_hours > max_stale_hours:
                rec.sync_state = "warn"
            else:
                rec.sync_state = "ok"
    
    @api.model
    def get_singleton(self):
        """Get or create the singleton sync state record"""
        record = self.search([], limit=1)
        if not record:
            record = self.create({"name": "Material Taxonomy Sync State"})
        return record

    def _check_integration_access(self):
        """Restrict taxonomy sync state writes to integration users unless sudo."""
        if not self.env.su and not self.env.user.has_group("itad_core.group_itad_integration"):
            raise AccessError("Only integration users may modify taxonomy sync state.")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Enforce singleton pattern"""
        self._check_integration_access()
        existing = self.search([], limit=1)
        if existing or len(vals_list) > 1:
            raise UserError(
                "Only one taxonomy sync state record is allowed. "
                "The existing record will be updated automatically by the sync engine."
            )
        return super().create(vals_list)

    def write(self, vals):
        self._check_integration_access()
        return super().write(vals)
