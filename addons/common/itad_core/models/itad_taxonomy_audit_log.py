# File: itad_core/models/itad_taxonomy_audit_log.py

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ItadTaxonomyAuditLog(models.Model):
    """
    Taxonomy Audit Log - Audit Trail for Taxonomy Operations
    
    Phase 2.3 Security: Tracks all taxonomy-related security events including
    sync attempts, break-glass usage, and stale overrides.
    """
    _name = "itad.taxonomy.audit.log"
    _description = "Taxonomy Audit Log"
    _order = "occurred_at desc"
    
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        help="User who triggered this event",
    )
    
    occurred_at = fields.Datetime(
        string="Occurred At",
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="Timestamp when event occurred",
    )
    
    action = fields.Selection(
        [
            ("sync_attempt", "Sync Attempt"),
            ("sync_success", "Sync Success"),
            ("sync_failure", "Sync Failure"),
            ("break_glass_enabled", "Break-Glass Enabled"),
            ("break_glass_disabled", "Break-Glass Disabled"),
            ("stale_override_used", "Stale Override Used"),
            ("validation_block", "Validation Block"),
            ("retention_delete", "Retention Delete"),  # Phase 2.4: Audit log deletion
        ],
        string="Action",
        required=True,
        index=True,
        help="Type of audit event",
    )
    
    details = fields.Text(
        string="Details",
        help="Additional context about the event (JSON or plain text)",
    )
    
    success = fields.Boolean(
        string="Success",
        default=True,
        help="Whether the operation succeeded",
    )
    
    error_message = fields.Text(
        string="Error Message",
        help="Error message if operation failed",
    )
    
    # Archive fields for retention policy
    archived = fields.Boolean(
        string="Archived",
        default=False,
        index=True,
        help="True if record has been archived per retention policy",
    )
    
    archived_at = fields.Datetime(
        string="Archived At",
        index=True,
        help="Timestamp when record was archived (never updated after first archival)",
    )
    
    @api.model
    def log_event(self, action, details=None, success=True, error_message=None):
        """
        Helper method to create audit log entry.
        
        Args:
            action: Selection value (sync_attempt, etc.)
            details: Additional context
            success: Boolean success flag
            error_message: Error message if applicable
        
        Returns:
            Created audit log record
        """
        return self.create({
            "action": action,
            "details": details,
            "success": success,
            "error_message": error_message,
        })
    
    @api.model
    def _cron_apply_retention_policy(self):
        """
        Apply retention policy to audit logs (Phase 2.3 extra hardening).
        
        Modes:
        - archive: Set archived=True for old records (never re-archive)
        - delete: Delete already-archived records older than retention + grace
        
        Config:
        - itad_core.taxonomy.audit_retention_days (default 365)
        - itad_core.taxonomy.audit_retention_mode (default "archive")
        - itad_core.taxonomy.audit_retention_grace_days (default 30)
        """
        from datetime import timedelta
        
        icp = self.env["ir.config_parameter"].sudo()
        
        retention_days = int(icp.get_param("itad_core.taxonomy.audit_retention_days", "365"))
        retention_mode = icp.get_param("itad_core.taxonomy.audit_retention_mode", "archive")
        grace_days = int(icp.get_param("itad_core.taxonomy.audit_retention_grace_days", "30"))
        
        now = fields.Datetime.now()
        archive_threshold = now - timedelta(days=retention_days)
        
        _logger.info(
            "Running audit retention policy: mode=%s, retention_days=%d, grace_days=%d",
            retention_mode, retention_days, grace_days
        )
        
        if retention_mode == "archive":
            # Archive old records (never re-archive - archived_at is immutable)
            to_archive = self.search([
                ("occurred_at", "<", archive_threshold),
                ("archived", "=", False),
            ])
            
            if to_archive:
                to_archive.write({
                    "archived": True,
                    "archived_at": now,
                })
                _logger.info("Archived %d audit log records", len(to_archive))
        
        elif retention_mode == "delete":
            # SECURITY: Delete mode requires explicit admin config
            # This is a two-phase delete: only already-archived records are eligible
            delete_enabled = icp.get_param("itad_core.taxonomy.audit_retention_delete_enabled", "false")
            if delete_enabled.lower() != "true":
                _logger.warning(
                    "Retention mode is 'delete' but delete not enabled. "
                    "Set itad_core.taxonomy.audit_retention_delete_enabled=true to allow deletion. "
                    "This is an admin-only config."
                )
                return
            
            # Delete already-archived records older than retention + grace
            delete_threshold = now - timedelta(days=retention_days + grace_days)
            
            to_delete = self.search([
                ("archived", "=", True),
                ("archived_at", "<", delete_threshold),
            ])
            
            if to_delete:
                count = len(to_delete)
                
                # AUDIT: Log permanent audit event BEFORE deletion (for compliance)
                # Create a new audit log with action 'retention_delete' 
                # This log itself will not be deleted (it happened now)
                self.create({
                    "action": "retention_delete",
                    "details": (
                        f"Deleted {count} archived audit logs. "
                        f"retention_days={retention_days}, grace_days={grace_days}, "
                        f"threshold={delete_threshold.isoformat()}, "
                        f"executed_by_cron=true"
                    ),
                    "success": True,
                })
                
                to_delete.unlink()
                _logger.info("Deleted %d archived audit log records (audit event logged)", count)
        
        else:
            _logger.warning("Unknown retention mode: %s (expected 'archive' or 'delete')", retention_mode)
