# File: itad_core/tests/test_receiving_wizard_hardening.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo import fields
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestReceivingWizardHardening(TransactionCase):
    """Phase 2.2 hardening tests for receiving wizard"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test FSM order with manifest data
        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
        cls.test_order = create_test_fsm_order(cls.env, cls.test_location, **{
            "name": "TEST-ORDER-001",
            "itad_pickup_manifest_id": "test-manifest-123",
            "itad_manifest_no": "MAN-2026-000001",
            "itad_bol_id": "BOL-2026-000123",
            "itad_receipt_state": "pending",
        })
        
        # Create receiving manager group
        cls.group_receiving_manager = cls.env.ref("itad_core.group_receiving_manager", raise_if_not_found=False)
        if not cls.group_receiving_manager:
            # Fallback if group not yet created
            cls.group_receiving_manager = cls.env["res.groups"].create({
                "name": "ITAD Receiving Manager",
            })
        cls.group_fsm_dispatcher = cls.env.ref("fieldservice.group_fsm_dispatcher")
        
        # Create test users
        cls.user_with_group = cls.env["res.users"].create({
            "name": "Receiving Manager",
            "login": "receiving_mgr",
            "groups_id": [
                (4, cls.group_receiving_manager.id),
                (4, cls.group_fsm_dispatcher.id),
            ],
        })
        
        cls.user_without_group = cls.env["res.users"].create({
            "name": "Regular User",
            "login": "regular_user",
            "groups_id": [(4, cls.env.ref("base.group_user").id)],
        })

    def _create_wizard(self, user=None):
        """Helper to create wizard instance"""
        target_user = user or self.user_with_group
        env = self.env if not target_user else self.env(user=target_user)
        return env["itad.receiving.wizard"].create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "material_type_code": "EW-CPU-001",
            "actual_weight_lbs": 150.5,
        })

    # ========== A) Configurable Defaults Tests ==========

    def test_get_receiving_defaults_fallback(self):
        """Test fallback defaults when system parameters are absent"""
        # Clear any existing params
        icp = self.env["ir.config_parameter"].sudo()
        icp.search([("key", "like", "itad_core.%")]).unlink()
        
        wizard = self._create_wizard()
        defaults = wizard._get_receiving_defaults()
        
        self.assertEqual(defaults["container_type"], "PALLET")
        self.assertEqual(defaults["scale_id"], "DOCK-SCALE-01")
        self.assertEqual(defaults["timeout"], 30)
        self.assertEqual(defaults["max_weight"], 100000)

    def test_get_receiving_defaults_overrides(self):
        """Test overrides when system parameters are set"""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.default_container_type", "GAYLORD")
        icp.set_param("itad_core.default_scale_id", "SCALE-02")
        icp.set_param("itad_core.receipt_timeout_seconds", "60")
        icp.set_param("itad_core.max_receipt_weight_lbs", "50000")
        
        wizard = self._create_wizard()
        defaults = wizard._get_receiving_defaults()
        
        self.assertEqual(defaults["container_type"], "GAYLORD")
        self.assertEqual(defaults["scale_id"], "SCALE-02")
        self.assertEqual(defaults["timeout"], 60)
        self.assertEqual(defaults["max_weight"], 50000)

    def test_build_payload_uses_configurable_defaults(self):
        """Test that payload building uses configurable defaults"""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.default_container_type", "DRUM")
        icp.set_param("itad_core.default_scale_id", "CUSTOM-SCALE")
        
        wizard = self._create_wizard()
        payload = wizard._build_receiving_payload()
        
        self.assertEqual(payload["container_type"], "DRUM")
        self.assertEqual(payload["scale_id"], "CUSTOM-SCALE")

    # ========== B) Idempotent Retry Tests ==========

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.fields.Datetime.now")
    def test_idempotent_retry_first_attempt_error(self, mock_now, mock_post, mock_get):
        """Test first attempt generates idempotency key and stores error"""
        fixed_time = fields.Datetime.to_datetime("2026-01-17 10:00:00")
        mock_now.return_value = fixed_time
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = Exception("No JSON")
        mock_post.return_value = mock_response
        
        wizard = self._create_wizard()
        
        # First attempt should fail
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm_receipt()

        self.assertIn("ITAD Core API error", str(ctx.exception))

        wizard._invalidate_cache(
            fnames=[
                "error_state",
                "last_error_message",
                "original_idempotency_key",
                "attempt_count",
                "last_attempt_at",
                "successful_at",
            ],
            ids=wizard.ids,
        )

        self.env.cr.execute(
            """
            SELECT error_state,
                   last_error_message,
                   original_idempotency_key,
                   attempt_count,
                   last_attempt_at,
                   successful_at
              FROM itad_receiving_wizard
             WHERE id = %s
            """,
            [wizard.id],
        )
        (
            error_state,
            last_error_message,
            original_idempotency_key,
            attempt_count,
            last_attempt_at,
            successful_at,
        ) = self.env.cr.fetchone()

        # Verify wizard state
        self.assertTrue(error_state)
        self.assertIn("500", last_error_message)
        self.assertTrue(original_idempotency_key)  # Key generated
        self.assertEqual(attempt_count, 1)
        self.assertEqual(last_attempt_at, fixed_time)
        self.assertFalse(successful_at)
        
        # Verify audit log created
        audit_logs = self.env["itad.receipt.audit.log"].sudo().search([
            ("manifest_no", "=", wizard.manifest_no)
        ])
        self.assertEqual(len(audit_logs), 1)
        self.assertFalse(audit_logs[0].success)
        self.assertEqual(audit_logs[0].attempt_number, 1)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.fields.Datetime.now")
    def test_idempotent_retry_reuses_key(self, mock_now, mock_post, mock_get):
        """Test retry reuses original idempotency key"""
        fixed_time = fields.Datetime.to_datetime("2026-01-17 10:00:00")
        mock_now.return_value = fixed_time
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        
        wizard = self._create_wizard()
        
        # Simulate first failed attempt
        wizard.write({
            "error_state": True,
            "last_error_message": "Previous error",
            "original_idempotency_key": "receipt-original-key-123",
            "attempt_count": 1,
            "last_attempt_at": fixed_time,
        })
        
        original_key = wizard.original_idempotency_key
        
        # Mock successful retry
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "rwrec-success-456",
            "bol_id": wizard.bol_id,
        }
        mock_post.return_value = mock_response
        
        # Retry
        wizard.action_retry_receipt()
        
        # Verify same idempotency key used
        self.assertEqual(wizard.original_idempotency_key, original_key)
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["headers"]["Idempotency-Key"], original_key)
        
        # Verify success state
        self.assertFalse(wizard.error_state)
        self.assertFalse(wizard.last_error_message)
        self.assertEqual(wizard.attempt_count, 2)
        self.assertEqual(wizard.successful_at, fixed_time)
        self.assertEqual(wizard.api_response_id, "rwrec-success-456")
        
        # Verify audit logs
        audit_logs = self.env["itad.receipt.audit.log"].sudo().search([
            ("manifest_no", "=", wizard.manifest_no)
        ], order="attempt_number")
        self.assertEqual(len(audit_logs), 1)  # Only retry creates log
        self.assertTrue(audit_logs[0].success)
        self.assertEqual(audit_logs[0].attempt_number, 2)
        self.assertEqual(audit_logs[0].response_id, "rwrec-success-456")

    # ========== C) RBAC Tests ==========

    def test_rbac_user_without_group_cannot_confirm(self):
        """Test user without receiving manager group cannot confirm receipt"""
        wizard = self._create_wizard()

        with self.assertRaises(AccessError):
            wizard.with_user(self.user_without_group).action_confirm_receipt()

    def test_rbac_user_with_group_can_confirm(self):
        """Test user with receiving manager group can confirm receipt"""
        wizard = self._create_wizard(user=self.user_with_group)
        
        with patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get") as mock_get, \
                patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post") as mock_post:
            mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "rwrec-123"}
            mock_post.return_value = mock_response
            
            # Should not raise AccessError
            result = wizard.action_confirm_receipt()
            self.assertEqual(result["type"], "ir.actions.client")

    # ========== D) Validation Tests ==========

    def test_validation_bol_format_valid(self):
        """Test valid BOL format passes validation"""
        wizard = self._create_wizard()
        wizard.bol_id = "BOL-2026-000123"
        
        # Should not raise
        wizard._validate_bol_format()

    def test_validation_bol_format_invalid(self):
        """Test invalid BOL format raises ValidationError"""
        wizard = self._create_wizard()
        wizard.bol_id = "BOL-2026-123"  # Too short
        
        with self.assertRaises(ValidationError) as ctx:
            wizard._validate_bol_format()
        
        self.assertIn("BOL format", str(ctx.exception))
        self.assertIn("BOL-YYYY-NNNNNN", str(ctx.exception))

    def test_validation_weight_zero(self):
        """Test weight <= 0 raises ValidationError"""
        wizard = self._create_wizard()
        wizard.actual_weight_lbs = 0
        
        with self.assertRaises(ValidationError) as ctx:
            wizard._validate_weight()
        
        self.assertIn("greater than zero", str(ctx.exception))

    def test_validation_weight_negative(self):
        """Test negative weight raises ValidationError"""
        wizard = self._create_wizard()
        wizard.actual_weight_lbs = -10.5
        
        with self.assertRaises(ValidationError) as ctx:
            wizard._validate_weight()
        
        self.assertIn("greater than zero", str(ctx.exception))

    def test_validation_weight_exceeds_max(self):
        """Test weight > max raises ValidationError"""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.max_receipt_weight_lbs", "1000")
        
        wizard = self._create_wizard()
        wizard.actual_weight_lbs = 1500
        
        with self.assertRaises(ValidationError) as ctx:
            wizard._validate_weight()
        
        self.assertIn("exceeds maximum", str(ctx.exception))
        self.assertIn("1000", str(ctx.exception))

    def test_validation_weight_within_range(self):
        """Test weight within range passes validation"""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.max_receipt_weight_lbs", "10000")
        
        wizard = self._create_wizard()
        wizard.actual_weight_lbs = 500.5
        
        # Should not raise
        wizard._validate_weight()

    # ========== E) Determinism Tests ==========

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.fields.Datetime.now")
    def test_deterministic_timestamps(self, mock_now):
        """Test timestamps use fields.Datetime.now for determinism"""
        fixed_time = fields.Datetime.to_datetime("2026-01-17 12:34:56")
        mock_now.return_value = fixed_time
        
        wizard = self._create_wizard()
        wizard._log_receipt_attempt(success=True, response_data={"id": "test-123"})
        
        self.assertEqual(wizard.last_attempt_at, fixed_time)
        self.assertEqual(wizard.successful_at, fixed_time)

    def test_no_datetime_utcnow_in_code(self):
        """Test code does not use datetime.utcnow()"""
        import inspect
        from odoo.addons.itad_core.models import itad_receiving_wizard
        
        source = inspect.getsource(itad_receiving_wizard)
        
        # Allow datetime.utcnow in comments but not in actual code
        lines = [line for line in source.split("\n") if not line.strip().startswith("#")]
        code_without_comments = "\n".join(lines)
        
        self.assertNotIn("datetime.utcnow()", code_without_comments,
                        "Code must use fields.Datetime.now() instead of datetime.utcnow()")
