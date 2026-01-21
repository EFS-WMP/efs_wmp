# File: itad_core/tests/test_receiving_wizard_taxonomy.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from odoo import fields
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestReceivingWizardTaxonomy(TransactionCase):
    """Phase 2.3: Tests for receiving wizard taxonomy validation"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test FSM order
        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
        cls.test_order = create_test_fsm_order(cls.env, cls.test_location, **{
            "name": "TEST-ORDER-TAX-001",
            "itad_pickup_manifest_id": "test-manifest-tax-123",
            "itad_manifest_no": "MAN-2026-TAX001",
            "itad_bol_id": "BOL-2026-000456",
            "itad_receipt_state": "pending",
        })
        
        # Create receiving manager
        cls.group_receiving_manager = cls.env.ref("itad_core.group_receiving_manager")
        cls.user_receiving_manager = cls.env["res.users"].create({
            "name": "Receiving Manager Tax Test",
            "login": "receiving_mgr_tax",
            "groups_id": [(4, cls.group_receiving_manager.id)],
        })

    def _create_material_type(self, **kwargs):
        """Helper to create material type in cache"""
        defaults = {
            "itad_core_uuid": "550e8400-e29b-41d4-a716-446655440099",
            "code": "TEST-MAT-001",
            "name": "Test Material",
            "stream": "test",
            "requires_photo": False,
            "requires_weight": False,
            "active": True,
        }
        defaults.update(kwargs)
        return self.env["itad.material.type.cache"].with_context(itad_sync=True).create(defaults)

    def test_wizard_domain_hides_inactive_material_types(self):
        """Test wizard domain filters out inactive material types"""
        # Create one active and one inactive
        active_mat = self._create_material_type(code="ACTIVE-001", active=True)
        inactive_mat = self._create_material_type(
            itad_core_uuid="550e8400-e29b-41d4-a716-446655440098",
            code="INACTIVE-001",
            active=False
        )

        # Check domain on material_type_id field
        wizard = self.env["itad.receiving.wizard"].new({
            "fsm_order_id": self.test_order.id,
        })
        
        field_def = self.env["itad.receiving.wizard"]._fields["material_type_id"]
        domain = field_def.get_domain_list(wizard)
        
        # Domain should filter active=True
        self.assertIn(("active", "=", True), domain)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    def test_wizard_requires_weight_blocks_if_missing_when_flag_true(self, mock_post, mock_get):
        """Test requires_weight=True blocks submission if weight missing/zero"""
        # Create material with requires_weight=True
        mat = self._create_material_type(requires_weight=True)

        # Create wizard with zero weight
        wizard = self.env["itad.receiving.wizard"].with_user(self.user_receiving_manager).create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "material_type_id": mat.id,
            "actual_weight_lbs": 0,  # Invalid
        })

        # Mock API responses
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})

        # Try to confirm - should fail
        with self.assertRaises(ValidationError) as ctx:
            wizard.action_confirm_receipt()

        self.assertIn("requires weight", str(ctx.exception))

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    def test_wizard_requires_photo_blocks_if_no_attachment_when_flag_true(self, mock_post, mock_get):
        """Test requires_photo=True blocks submission if no attachments"""
        # Create material with requires_photo=True
        mat = self._create_material_type(requires_photo=True)

        # Create wizard WITHOUT attachments
        wizard = self.env["itad.receiving.wizard"].with_user(self.user_receiving_manager).create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "material_type_id": mat.id,
            "actual_weight_lbs": 100.0,
        })

        # Mock API responses
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})

        # Try to confirm - should fail
        with self.assertRaises(ValidationError) as ctx:
            wizard.action_confirm_receipt()

        self.assertIn("requires photo", str(ctx.exception))

    def test_wizard_degraded_mode_blocks_if_no_active_cache(self):
        """Test wizard blocks if cache has 0 active records"""
        # Ensure no active cache records
        self.env["itad.material.type.cache"].search([]).with_context(itad_sync=True).write({"active": False})

        # Create wizard
        wizard = self.env["itad.receiving.wizard"].with_user(self.user_receiving_manager).create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "actual_weight_lbs": 100.0,
        })

        # Try to confirm - should fail
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm_receipt()

        self.assertIn("not synced", str(ctx.exception).lower())

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.fields.Datetime.now")
    def test_wizard_degraded_mode_blocks_if_stale_sync(self, mock_now):
        """Test wizard blocks if sync is stale and block_if_stale=true"""
        from datetime import datetime, timedelta

        # Create active material so cache is not empty
        self._create_material_type()

        # Set sync state to stale (26 hours ago, max_stale_hours default is 24)
        now = datetime(2026, 1, 18, 12, 0, 0)
        stale_time = now - timedelta(hours=26)
        mock_now.return_value = now

        sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
        sync_state.write({"last_success_at": stale_time})

        # Ensure block_if_stale is true (default)
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.taxonomy.sync.block_if_stale", "true")

        # Create wizard
        wizard = self.env["itad.receiving.wizard"].with_user(self.user_receiving_manager).create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "material_type_id": self.env["itad.material.type.cache"].search([], limit=1).id,
            "actual_weight_lbs": 100.0,
        })

        # Try to confirm - should fail
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm_receipt()

        self.assertIn("stale", str(ctx.exception).lower())
