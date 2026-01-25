# File: itad_core/tests/test_receiving_rate_limit.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields
from datetime import timedelta
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
    ensure_taxonomy_sync_state,
    seed_taxonomy_cache,
)


class TestReceivingRateLimit(TransactionCase):
    """Test rate limiting for receipt attempts"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
        cls.test_order = create_test_fsm_order(cls.env, cls.test_location, **{
            "name": "TEST-ORDER-RATELIMIT",
            "itad_pickup_manifest_id": "test-manifest-ratelimit",
            "itad_manifest_no": "MAN-2026-777777",
            "itad_bol_id": "BOL-2026-000777",
            "itad_receipt_state": "pending",
        })
        
        cls.group_receiving_manager = cls.env.ref("itad_core.group_receiving_manager")
        cls.group_fsm_dispatcher = cls.env.ref("fieldservice.group_fsm_dispatcher")
        cls.test_user = cls.env["res.users"].create({
            "name": "RateLimit Test User",
            "login": "ratelimit_test",
            "groups_id": [
                (4, cls.group_receiving_manager.id),
                (4, cls.group_fsm_dispatcher.id),
            ],
        })
        seed_taxonomy_cache(cls.env)
        ensure_taxonomy_sync_state(cls.env)

    def _create_wizard(self):
        return self.env["itad.receiving.wizard"].with_user(self.test_user).create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "material_type_code": "EW-CPU-001",
            "actual_weight_lbs": 100.0,
        })

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_rate_limit_blocks_excessive_attempts(self, mock_get, mock_post):
        """Test rate limit blocks when max attempts per hour exceeded"""
        # Set max attempts to 3
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.max_receipt_attempts_per_hour", "3"
        )

        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        
        # Mock time to fixed value
        fixed_time = fields.Datetime.to_datetime("2026-01-17 12:00:00")
        
        # Create 3 audit log entries within last hour
        for i in range(3):
            self.env["itad.receipt.audit.log"].create({
                "order_id": self.test_order.id,
                "user_id": self.test_user.id,
                "manifest_no": self.test_order.itad_manifest_no,
                "bol_id": self.test_order.itad_bol_id,
                "success": False,
                "outcome": "SERVER_ERROR",
                "attempt_number": i + 1,
                "attempted_at": fields.Datetime.to_string(
                    fixed_time - timedelta(minutes=30)
                ),
            })
        
        # Mock wizard._now() to return fixed time
        wizard = self._create_wizard()
        
        with patch(
            "odoo.addons.itad_core.models.itad_receiving_wizard.ItadReceivingWizard._now",
            return_value=fixed_time,
        ):
            with self.assertRaises(UserError) as ctx:
                wizard.action_confirm_receipt()
        
        # Error should mention rate limit
        error_msg = str(ctx.exception).lower()
        self.assertTrue("rate" in error_msg or "limit" in error_msg or "too many" in error_msg)
        
        # POST should NOT have been called
        self.assertFalse(mock_post.called)
        
        # Should create audit log with RATE_LIMIT_BLOCK
        self.env.cr.execute(
            """
            SELECT count(*)
              FROM itad_receipt_audit_log
             WHERE order_id = %s
               AND outcome = 'RATE_LIMIT_BLOCK'
            """,
            [wizard.fsm_order_id.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_rate_limit_allows_within_limit(self, mock_get, mock_post):
        """Test rate limit allows attempts within limit"""
        # Set max attempts to 5
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.max_receipt_attempts_per_hour", "5"
        )
        
        fixed_time = fields.Datetime.to_datetime("2026-01-17 12:00:00")
        
        # Create 3 audit log entries (under limit of 5)
        for i in range(3):
            self.env["itad.receipt.audit.log"].create({
                "order_id": self.test_order.id,
                "user_id": self.test_user.id,
                "manifest_no": self.test_order.itad_manifest_no,
                "bol_id": self.test_order.itad_bol_id,
                "success": False,
                "outcome": "SERVER_ERROR",
                "attempt_number": i + 1,
                "attempted_at": fields.Datetime.to_string(
                    fixed_time - timedelta(minutes=30)
                ),
            })
        
        # Mock health check and POST
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-ratelimit-ok"}
        )
        
        wizard = self._create_wizard()
        
        with patch(
            "odoo.addons.itad_core.models.itad_receiving_wizard.ItadReceivingWizard._now",
            return_value=fixed_time,
        ):
            result = wizard.action_confirm_receipt()
        
        # Should succeed
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertTrue(mock_post.called)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_rate_limit_ignores_old_attempts(self, mock_get, mock_post):
        """Test rate limit ignores attempts older than 1 hour"""
        # Set max attempts to 3
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.max_receipt_attempts_per_hour", "3"
        )
        
        fixed_time = fields.Datetime.to_datetime("2026-01-17 12:00:00")
        
        # Create 5 audit log entries, but all older than 1 hour
        for i in range(5):
            self.env["itad.receipt.audit.log"].create({
                "order_id": self.test_order.id,
                "user_id": self.test_user.id,
                "manifest_no": self.test_order.itad_manifest_no,
                "bol_id": self.test_order.itad_bol_id,
                "success": False,
                "outcome": "SERVER_ERROR",
                "attempt_number": i + 1,
                "attempted_at": fields.Datetime.to_string(
                    fixed_time - timedelta(hours=2)
                ),  # 2 hours ago
            })
        
        # Mock health check and POST
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-old-attempts-ok"}
        )
        
        wizard = self._create_wizard()
        
        with patch(
            "odoo.addons.itad_core.models.itad_receiving_wizard.ItadReceivingWizard._now",
            return_value=fixed_time,
        ):
            result = wizard.action_confirm_receipt()
        
        # Should succeed (old attempts don't count)
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertTrue(mock_post.called)
