# File: itad_core/tests/test_variance.py
"""
Phase 2.5: Variance Detection and Resolution Tests
"""

from odoo.tests.common import TransactionCase
from odoo import fields

from ._helpers import create_test_fsm_order, create_test_location, create_test_partner


class TestVariance(TransactionCase):
    """Test variance detection and resolution workflow."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.icp = cls.env["ir.config_parameter"].sudo()
        cls.fsm_order = cls.env["fsm.order"]
        
        # Create test location
        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
    
    def _now(self):
        return fields.Datetime.now()
    
    def _create_order(self, weight=1000, receipt_state="received"):
        """Helper to create test order."""
        return create_test_fsm_order(self.env, self.test_location, **{
            "itad_receipt_state": receipt_state,
            "itad_receipt_weight_lbs": weight,
            "itad_receipt_confirmed_at": self._now(),
            "itad_variance_review_state": "none",
        })
    
    def test_variance_flagging_exceeds_max_weight(self):
        """Test variance flagged when weight exceeds max threshold."""
        # Set max weight
        self.icp.set_param("itad_core.max_receipt_weight_lbs", "50000")
        
        # Create order with weight > max
        order = self._create_order(weight=60000)
        
        # Evaluate variance
        flag, reason = order._evaluate_variance_for_order()
        
        self.assertTrue(flag)
        self.assertIn("exceeds max", reason)
    
    def test_variance_no_flag_normal_weight(self):
        """Test no variance when weight is normal."""
        self.icp.set_param("itad_core.max_receipt_weight_lbs", "50000")
        
        order = self._create_order(weight=5000)
        
        flag, reason = order._evaluate_variance_for_order()
        
        self.assertFalse(flag)
        self.assertEqual(reason, "")
    
    def test_variance_resolve_action(self):
        """Test variance resolution sets reviewed fields."""
        order = self._create_order(weight=60000)
        order.write({
            "itad_variance_flag": True,
            "itad_variance_reason": "Test variance",
            "itad_variance_review_state": "pending",
        })
        
        # Resolve
        order.action_resolve_variance()
        
        self.assertEqual(order.itad_variance_review_state, "resolved")
        self.assertEqual(order.itad_variance_reviewed_by, self.env.user)
        self.assertTrue(order.itad_variance_reviewed_at)
    
    def test_variance_resolve_only_pending(self):
        """Test resolve only affects pending state."""
        order = self._create_order()
        order.write({"itad_variance_review_state": "none"})
        
        # Try to resolve (should not change anything)
        order.action_resolve_variance()
        
        self.assertEqual(order.itad_variance_review_state, "none")
        self.assertFalse(order.itad_variance_reviewed_by)
    
    def test_cron_evaluate_variance(self):
        """Test cron evaluates recent received orders."""
        self.icp.set_param("itad_core.max_receipt_weight_lbs", "50000")
        
        # Create orders
        normal = self._create_order(weight=5000)
        exceeds = self._create_order(weight=60000)
        
        # Run cron
        self.fsm_order._cron_evaluate_variance()
        
        # Check results
        self.assertFalse(normal.itad_variance_flag)
        self.assertTrue(exceeds.itad_variance_flag)
        self.assertEqual(exceeds.itad_variance_review_state, "pending")
