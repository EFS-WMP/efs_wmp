# File: itad_core/tests/test_receiving_api_compat_check.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
    ensure_taxonomy_sync_state,
    seed_taxonomy_cache,
)


class TestReceivingAPICompatCheck(TransactionCase):
    """Test API health and version compatibility checks"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
        cls.test_order = create_test_fsm_order(cls.env, cls.test_location, **{
            "name": "TEST-ORDER-COMPAT",
            "itad_pickup_manifest_id": "test-manifest-compat",
            "itad_manifest_no": "MAN-2026-888888",
            "itad_bol_id": "BOL-2026-000888",
            "itad_receipt_state": "pending",
        })
        
        cls.group_receiving_manager = cls.env.ref("itad_core.group_receiving_manager")
        cls.group_fsm_dispatcher = cls.env.ref("fieldservice.group_fsm_dispatcher")
        cls.test_user = cls.env["res.users"].create({
            "name": "Compat Test User",
            "login": "compat_test",
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
    def test_health_check_success_allows_submission(self, mock_get, mock_post):
        """Test /health returns 200 -> allow submission"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-health-ok"}
        )
        
        wizard = self._create_wizard()
        result = wizard.action_confirm_receipt()
        
        # Should succeed
        self.assertEqual(result["type"], "ir.actions.client")
        # POST should have been called
        self.assertTrue(mock_post.called)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_health_fail_openapi_success_allows_submission(self, mock_get, mock_post):
        """Test /health fails but /openapi.json returns version 1.2.0 -> allow"""
        def get_side_effect(url, **kwargs):
            if "/health" in url:
                return Mock(status_code=404)
            elif "/openapi.json" in url:
                return Mock(
                    status_code=200,
                    json=lambda: {"info": {"version": "1.2.0"}}
                )
            return Mock(status_code=404)
        
        mock_get.side_effect = get_side_effect
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-openapi-ok"}
        )
        
        wizard = self._create_wizard()
        result = wizard.action_confirm_receipt()
        
        # Should succeed
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertTrue(mock_post.called)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_version_too_old_blocks_submission(self, mock_get, mock_post):
        """Test /openapi.json returns version 0.9.9 -> block with API_VERSION_UNSUPPORTED"""
        def get_side_effect(url, **kwargs):
            if "/health" in url:
                return Mock(status_code=404)
            elif "/openapi.json" in url:
                return Mock(
                    status_code=200,
                    json=lambda: {"info": {"version": "0.9.9"}}
                )
            return Mock(status_code=404)
        
        mock_get.side_effect = get_side_effect
        
        wizard = self._create_wizard()
        
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm_receipt()
        
        # Should mention version
        self.assertIn("version", str(ctx.exception).lower())
        
        # POST should NOT have been called
        self.assertFalse(mock_post.called)
        
        # Should create audit log with API_VERSION_UNSUPPORTED
        self.env.cr.execute(
            """
            SELECT outcome
              FROM itad_receipt_audit_log
             WHERE order_id = %s
            """,
            [wizard.fsm_order_id.id],
        )
        rows = self.env.cr.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "API_VERSION_UNSUPPORTED")

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_both_endpoints_fail_blocks_submission(self, mock_get, mock_post):
        """Test both /health and /openapi.json fail -> block with API_UNREACHABLE"""
        mock_get.return_value = Mock(status_code=500)
        
        wizard = self._create_wizard()
        
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm_receipt()
        
        # Should mention unreachable/connection
        error_msg = str(ctx.exception).lower()
        self.assertTrue("unreachable" in error_msg or "connection" in error_msg or "health" in error_msg)
        
        # POST should NOT have been called
        self.assertFalse(mock_post.called)
        
        # Should create audit log with API_UNREACHABLE
        self.env.cr.execute(
            """
            SELECT outcome
              FROM itad_receipt_audit_log
             WHERE order_id = %s
            """,
            [wizard.fsm_order_id.id],
        )
        rows = self.env.cr.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "API_UNREACHABLE")
