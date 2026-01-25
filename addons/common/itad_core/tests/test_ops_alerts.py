# File: itad_core/tests/test_ops_alerts.py
"""
Phase 2.5: Operations Alerts Tests
"""

from datetime import timedelta

from odoo.tests.common import TransactionCase
from odoo import fields

from ._helpers import create_test_fsm_order, create_test_location, create_test_partner


class TestOpsAlerts(TransactionCase):
    """Test operations alert computation."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alert_model = cls.env["itad.ops.alert"]
        cls.icp = cls.env["ir.config_parameter"].sudo()
    
    def _now(self):
        """Get current time via Odoo method."""
        return fields.Datetime.now()
    
    def test_ops_alerts_taxonomy_stale_critical(self):
        """Test taxonomy stale alert triggers critical when > 2x threshold."""
        # Set threshold
        self.icp.set_param("itad_core.taxonomy.sync.max_stale_hours", "24")
        
        # Set last_success_at > 48 hours ago (critical)
        sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
        stale_time = self._now() - timedelta(hours=72)
        sync_state.write({"last_success_at": stale_time, "last_error": False})
        
        # Compute alerts
        self.alert_model._compute_taxonomy_stale_alert()
        
        # Verify
        alert = self.alert_model.search([("code", "=", "TAXONOMY_STALE")], limit=1)
        self.assertTrue(alert, "Alert should exist")
        self.assertEqual(alert.severity, "critical")
        self.assertIn("72", alert.message)  # Should show stale hours
    
    def test_ops_alerts_taxonomy_stale_warn(self):
        """Test taxonomy stale alert triggers warning when > threshold."""
        self.icp.set_param("itad_core.taxonomy.sync.max_stale_hours", "24")
        
        # Set last_success_at > 24 but < 48 hours ago (warning)
        sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
        stale_time = self._now() - timedelta(hours=36)
        sync_state.write({"last_success_at": stale_time, "last_error": False})
        
        self.alert_model._compute_taxonomy_stale_alert()
        
        alert = self.alert_model.search([("code", "=", "TAXONOMY_STALE")], limit=1)
        self.assertEqual(alert.severity, "warn")
    
    def test_ops_alerts_taxonomy_stale_ok(self):
        """Test taxonomy stale alert is OK when recent sync."""
        self.icp.set_param("itad_core.taxonomy.sync.max_stale_hours", "24")
        
        # Set last_success_at to 1 hour ago
        sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
        recent_time = self._now() - timedelta(hours=1)
        sync_state.write({"last_success_at": recent_time, "last_error": False})
        
        self.alert_model._compute_taxonomy_stale_alert()
        
        alert = self.alert_model.search([("code", "=", "TAXONOMY_STALE")], limit=1)
        self.assertEqual(alert.severity, "ok")
    
    def test_ops_alerts_outbox_failures(self):
        """Test outbox failures alert triggers when > threshold."""
        self.icp.set_param("itad_core.ops.outbox_failures_threshold", "5")
        self.icp.set_param("itad_core.ops.outbox_window_minutes", "60")
        
        # Create failed outbox records
        partner = create_test_partner(self.env)
        location = create_test_location(self.env, partner)
        fsm_order = create_test_fsm_order(self.env, location)
        
        for i in range(7):
            self.env["itad.core.outbox"].create({
                "order_id": fsm_order.id,
                "idempotency_key": f"test-fail-{i}",
                "correlation_id": f"corr-{i}",
                "state": "failed",
                "last_error": "Test error",
            })
        
        self.alert_model._compute_outbox_failures_alert()
        
        alert = self.alert_model.search([("code", "=", "OUTBOX_FAILURES")], limit=1)
        self.assertEqual(alert.severity, "critical")
        self.assertGreaterEqual(alert.metric_value, 7)
    
    def test_ops_alerts_retention_delete_enabled(self):
        """Test retention delete alert triggers critical when delete enabled."""
        self.icp.set_param("itad_core.taxonomy.audit_retention_mode", "delete")
        self.icp.set_param("itad_core.taxonomy.audit_retention_delete_enabled", "true")
        
        self.alert_model._compute_retention_delete_alert()
        
        alert = self.alert_model.search([("code", "=", "RETENTION_DELETE_ENABLED")], limit=1)
        self.assertEqual(alert.severity, "critical")
        self.assertIn("DELETE", alert.message.upper())
    
    def test_ops_alerts_retention_delete_disabled(self):
        """Test retention delete alert is OK when in archive mode."""
        self.icp.set_param("itad_core.taxonomy.audit_retention_mode", "archive")
        self.icp.set_param("itad_core.taxonomy.audit_retention_delete_enabled", "false")
        
        self.alert_model._compute_retention_delete_alert()
        
        alert = self.alert_model.search([("code", "=", "RETENTION_DELETE_ENABLED")], limit=1)
        self.assertEqual(alert.severity, "ok")
    
    def test_compute_alerts_idempotent(self):
        """Test compute_alerts is idempotent."""
        # Run twice
        self.alert_model.compute_alerts()
        count1 = self.alert_model.search_count([])
        
        self.alert_model.compute_alerts()
        count2 = self.alert_model.search_count([])
        
        self.assertEqual(count1, count2, "Should not create duplicates")
