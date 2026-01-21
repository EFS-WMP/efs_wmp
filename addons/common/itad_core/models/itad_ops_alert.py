# File: itad_core/models/itad_ops_alert.py
"""
Phase 2.5: Operations Alert Model

Tracks operational health alerts for receiving managers.
Recomputed periodically by cron job.
"""

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# Alert codes - must match UI references
ALERT_TAXONOMY_STALE = "TAXONOMY_STALE"
ALERT_OUTBOX_FAILURES = "OUTBOX_FAILURES"
ALERT_RETENTION_DELETE = "RETENTION_DELETE_ENABLED"


class ItadOpsAlert(models.Model):
    """
    Operations Alert - Tracks health conditions for Ops dashboard.
    
    Phase 2.5: Each alert is upserted by code during compute_alerts().
    UI displays these as cards on Operations Health dashboard.
    """
    _name = "itad.ops.alert"
    _description = "Operations Alert"
    _order = "severity desc, code"
    _rec_name = "code"
    
    code = fields.Char(
        string="Alert Code",
        required=True,
        index=True,
        help="Unique alert code (e.g., TAXONOMY_STALE)",
    )
    
    severity = fields.Selection(
        [
            ("ok", "OK"),
            ("warn", "Warning"),
            ("critical", "Critical"),
        ],
        string="Severity",
        default="ok",
        required=True,
        index=True,
    )
    
    message = fields.Text(
        string="Message",
        help="Human-readable alert message",
    )
    
    metric_value = fields.Float(
        string="Metric Value",
        help="Current value of the metric being tracked",
    )
    
    threshold_value = fields.Float(
        string="Threshold",
        help="Threshold that triggers alert",
    )
    
    last_evaluated_at = fields.Datetime(
        string="Last Evaluated",
        readonly=True,
    )
    
    action_hint = fields.Char(
        string="Recommended Action",
        help="Short action description (e.g., 'Sync now')",
    )
    
    action_ref = fields.Char(
        string="Action Reference",
        help="XML ID of action to open (e.g., itad_core.action_sync_status)",
    )
    
    _sql_constraints = [
        ("unique_code", "UNIQUE(code)", "Alert code must be unique"),
    ]
    
    @api.model
    def _get_config_param(self, key, default):
        """Get system parameter with default."""
        return self.env["ir.config_parameter"].sudo().get_param(key, default)
    
    @api.model
    def _upsert_alert(self, code, severity, message, metric_value, threshold_value, action_hint, action_ref=None):
        """
        Upsert alert record by code (idempotent).
        """
        now = fields.Datetime.now()
        existing = self.search([("code", "=", code)], limit=1)
        
        vals = {
            "code": code,
            "severity": severity,
            "message": message,
            "metric_value": metric_value,
            "threshold_value": threshold_value,
            "last_evaluated_at": now,
            "action_hint": action_hint,
            "action_ref": action_ref,
        }
        
        if existing:
            existing.write(vals)
            return existing
        else:
            return self.create(vals)
    
    @api.model
    def _compute_taxonomy_stale_alert(self):
        """Evaluate taxonomy sync stale condition."""
        sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
        
        max_stale_hours = int(self._get_config_param(
            "itad_core.taxonomy.sync.max_stale_hours", "24"
        ))
        warn_threshold = max_stale_hours
        critical_threshold = max_stale_hours * 2
        
        now = fields.Datetime.now()
        stale_age_hours = 0
        
        if sync_state.last_success_at:
            delta = now - sync_state.last_success_at
            stale_age_hours = delta.total_seconds() / 3600
        else:
            # Never synced = critical
            stale_age_hours = 9999
        
        if stale_age_hours > critical_threshold:
            severity = "critical"
            message = f"Taxonomy sync is {stale_age_hours:.1f}h stale (critical > {critical_threshold}h)"
        elif stale_age_hours > warn_threshold:
            severity = "warn"
            message = f"Taxonomy sync is {stale_age_hours:.1f}h stale (warning > {warn_threshold}h)"
        else:
            severity = "ok"
            message = f"Taxonomy sync healthy ({stale_age_hours:.1f}h ago)"
        
        self._upsert_alert(
            code=ALERT_TAXONOMY_STALE,
            severity=severity,
            message=message,
            metric_value=stale_age_hours,
            threshold_value=warn_threshold,
            action_hint="Sync now" if severity != "ok" else "",
            action_ref="itad_core.action_taxonomy_sync_state",
        )
    
    @api.model
    def _compute_outbox_failures_alert(self):
        """Evaluate outbox failure count in time window."""
        threshold = int(self._get_config_param(
            "itad_core.ops.outbox_failures_threshold", "5"
        ))
        window_minutes = int(self._get_config_param(
            "itad_core.ops.outbox_window_minutes", "60"
        ))
        
        now = fields.Datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Count failed outbox records in window
        failed_count = self.env["itad.core.outbox"].search_count([
            ("state", "=", "failed"),
            ("write_date", ">=", window_start),
        ])
        
        if failed_count > threshold:
            severity = "critical"
            message = f"{failed_count} outbox failures in last {window_minutes} min (threshold: {threshold})"
        elif failed_count > 0:
            severity = "warn"
            message = f"{failed_count} outbox failure(s) in last {window_minutes} min"
        else:
            severity = "ok"
            message = f"No outbox failures in last {window_minutes} min"
        
        self._upsert_alert(
            code=ALERT_OUTBOX_FAILURES,
            severity=severity,
            message=message,
            metric_value=failed_count,
            threshold_value=threshold,
            action_hint="Open outbox" if failed_count > 0 else "",
            action_ref="itad_core.action_outbox_failed",
        )
    
    @api.model
    def _compute_retention_delete_alert(self):
        """Evaluate if retention delete mode is enabled (break-glass)."""
        retention_mode = self._get_config_param(
            "itad_core.taxonomy.audit_retention_mode", "archive"
        )
        delete_enabled = self._get_config_param(
            "itad_core.taxonomy.audit_retention_delete_enabled", "false"
        )
        
        is_delete_active = (
            retention_mode == "delete" and 
            delete_enabled.lower() == "true"
        )
        
        if is_delete_active:
            severity = "critical"
            message = "Retention DELETE mode is ENABLED (break-glass). Audit logs will be permanently deleted."
        elif retention_mode == "delete":
            severity = "warn"
            message = "Retention mode is 'delete' but not enabled. Set delete_enabled=true to activate."
        else:
            severity = "ok"
            message = f"Retention mode: {retention_mode} (safe - logs are archived, not deleted)"
        
        self._upsert_alert(
            code=ALERT_RETENTION_DELETE,
            severity=severity,
            message=message,
            metric_value=1 if is_delete_active else 0,
            threshold_value=0,
            action_hint="Disable delete mode" if is_delete_active else "",
            action_ref="",  # System parameters - manual
        )
    
    @api.model
    def compute_alerts(self):
        """
        Recompute all alert conditions (called by cron).
        
        Idempotent - safe to call multiple times.
        """
        _logger.info("Computing operations alerts...")
        
        self._compute_taxonomy_stale_alert()
        self._compute_outbox_failures_alert()
        self._compute_retention_delete_alert()
        
        _logger.info("Operations alerts computed successfully")
        return True
    
    @api.model
    def _cron_compute_alerts(self):
        """Cron job entry point."""
        return self.compute_alerts()
