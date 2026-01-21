# File: itad_core/models/itad_receipt_audit_log.py

from odoo import fields, models


class ItadReceiptAuditLog(models.Model):
    _name = "itad.receipt.audit.log"
    _description = "ITAD Receipt Audit Log"
    _order = "attempted_at desc"

    wizard_id = fields.Integer(
        string="Wizard ID",
        readonly=True,
        help="Wizard record ID (transient records are not linkable)",
    )
    
    order_id = fields.Many2one(
        "fsm.order",
        string="FSM Order",
        readonly=True,
        index=True,
    )
    
    user_id = fields.Many2one(
        "res.users",
        string="User",
        readonly=True,
        index=True,
        help="User who attempted the receipt",
    )
    
    manifest_no = fields.Char(
        string="Manifest No",
        readonly=True,
        index=True,
    )
    
    bol_id = fields.Char(
        string="BOL ID",
        readonly=True,
        help="Bill of Lading ID",
    )
    
    success = fields.Boolean(
        string="Success",
        readonly=True,
        default=False,
    )
    
    outcome = fields.Selection(
        selection=[
            ("SUCCESS", "Success"),
            ("API_UNREACHABLE", "API Unreachable"),
            ("API_VERSION_UNSUPPORTED", "API Version Unsupported"),
            ("VALIDATION_ERROR", "Validation Error"),
            ("SERVER_ERROR", "Server Error"),
            ("RATE_LIMIT_BLOCK", "Rate Limit Block"),
            ("DUPLICATE_RETURNED", "Duplicate Returned"),
        ],
        string="Outcome",
        readonly=True,
        help="Outcome of the receipt attempt",
    )
    
    attempt_number = fields.Integer(
        string="Attempt Number",
        readonly=True,
        required=True,
    )
    
    error_message = fields.Text(
        string="Error Message",
        readonly=True,
    )
    
    response_id = fields.Char(
        string="Response ID",
        readonly=True,
        help="ITAD Core receiving_weight_record_id if successful",
    )
    
    attempted_at = fields.Datetime(
        string="Attempted At",
        readonly=True,
        required=True,
        default=lambda self: fields.Datetime.now(),
        index=True,
    )
    
    idempotency_key = fields.Char(
        string="Idempotency Key",
        readonly=True,
        index=True,
    )
    
    correlation_id = fields.Char(
        string="Correlation ID",
        readonly=True,
        index=True,
    )
    
    # Phase 2.2a: Archiving fields
    archived = fields.Boolean(
        string="Archived",
        readonly=True,
        default=False,
        help="True if this log has been archived per retention policy",
    )
    
    archived_at = fields.Datetime(
        string="Archived At",
        readonly=True,
        help="When this log was archived",
    )
    
    def _now(self):
        """Deterministic time wrapper for testing"""
        return fields.Datetime.now()
    
    def _cron_archive_old_receipt_audit_logs(self):
        """
        Archive audit logs older than retention period.
        
        Phase 2.2a: Cron job to mark old logs as archived.
        """
        icp = self.env["ir.config_parameter"].sudo()
        retention_days = int(icp.get_param("itad_core.audit_retention_days", "180"))
        
        now = self._now()
        from datetime import timedelta
        cutoff = now - timedelta(days=retention_days)
        cutoff_str = fields.Datetime.to_string(cutoff)
        
        # Find logs older than cutoff that aren't already archived
        self.env.cr.execute(
            """
            UPDATE itad_receipt_audit_log
               SET archived = TRUE,
                   archived_at = %s
             WHERE attempted_at < %s
               AND archived = FALSE
            """,
            [now, cutoff_str],
        )

