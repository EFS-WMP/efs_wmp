# File: itad_core/tests/test_evidence_pack.py
"""
Phase 2.7: Evidence Pack Tests

Tests for:
- Access control (manager only)
- Happy path (JSON+PDF generated)
- Hash integrity
"""

from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestEvidencePack(TransactionCase):
    """Test Evidence Pack generation."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.evidence_service = cls.env["itad.evidence.pack.service"]
        
        # Create test location
        cls.test_location = cls.env["fsm.location"].create({"name": "Test Location"})
        
        # Create test order with required fields
        cls.test_order = cls.env["fsm.order"].create({
            "location_id": cls.test_location.id,
            "itad_bol_id": "BOL-2026-TEST001",
            "itad_manifest_no": "MAN-TEST001",
            "itad_receipt_state": "received",
        })
        
        # Create outbox record
        cls.env["itad.core.outbox"].create({
            "order_id": cls.test_order.id,
            "idempotency_key": "test-idem-key",
            "correlation_id": "test-corr-id",
            "state": "sent",
        })
        
        # Get manager user
        cls.manager_user = cls.env.ref("base.user_admin")
    
    def test_access_control_non_manager_denied(self):
        """Test non-manager cannot generate evidence pack."""
        # Create user without manager role
        user = self.env["res.users"].create({
            "name": "Test User",
            "login": "test_user_no_role",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        
        # Try to generate as non-manager
        with self.assertRaises(AccessError):
            self.evidence_service.with_user(user).generate_for_order(self.test_order.id)
    
    def test_access_control_manager_allowed(self):
        """Test manager can generate evidence pack."""
        # Mock ITAD Core API calls
        with patch("odoo.addons.itad_core.models.itad_evidence_pack.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True, json=lambda: [])
            
            result = self.evidence_service.with_user(self.manager_user).generate_for_order(
                self.test_order.id
            )
            
            self.assertIn("pack_id", result)
            self.assertIn("json_attachment_id", result)
            self.assertIn("pdf_attachment_id", result)
    
    def test_happy_path_generates_attachments(self):
        """Test evidence pack generates JSON and PDF attachments."""
        with patch("odoo.addons.itad_core.models.itad_evidence_pack.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True, json=lambda: [])
            
            result = self.evidence_service.with_user(self.manager_user).generate_for_order(
                self.test_order.id
            )
            
            # Verify attachments created
            json_att = self.env["ir.attachment"].browse(result["json_attachment_id"])
            pdf_att = self.env["ir.attachment"].browse(result["pdf_attachment_id"])
            
            self.assertTrue(json_att.exists())
            self.assertTrue(pdf_att.exists())
            self.assertIn("EvidencePack-", json_att.name)
            self.assertIn(".json", json_att.name)
    
    def test_json_contains_required_keys(self):
        """Test JSON contains required schema keys."""
        import base64
        import json
        
        with patch("odoo.addons.itad_core.models.itad_evidence_pack.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True, json=lambda: [])
            
            result = self.evidence_service.with_user(self.manager_user).generate_for_order(
                self.test_order.id
            )
            
            json_att = self.env["ir.attachment"].browse(result["json_attachment_id"])
            pack = json.loads(base64.b64decode(json_att.datas))
            
            # Check required keys
            self.assertIn("meta", pack)
            self.assertIn("trace", pack)
            self.assertIn("odoo", pack)
            self.assertIn("itad_core", pack)
            self.assertIn("retention_and_controls", pack)
            self.assertIn("integrity", pack)
            
            # Check meta
            self.assertIn("pack_id", pack["meta"])
            self.assertIn("schema_version", pack["meta"])
            self.assertEqual(pack["meta"]["schema_version"], "1.0")
            
            # Check trace
            self.assertIn("correlation_ids", pack["trace"])
            self.assertIn("idempotency_keys", pack["trace"])
            self.assertIn("test-corr-id", pack["trace"]["correlation_ids"])
    
    def test_hash_integrity(self):
        """Test hash integrity is computed."""
        import base64
        import json
        
        with patch("odoo.addons.itad_core.models.itad_evidence_pack.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True, json=lambda: [])
            
            result = self.evidence_service.with_user(self.manager_user).generate_for_order(
                self.test_order.id
            )
            
            json_att = self.env["ir.attachment"].browse(result["json_attachment_id"])
            pack = json.loads(base64.b64decode(json_att.datas))
            
            # Verify hashes are present
            self.assertTrue(pack["integrity"]["json_sha256"])
            self.assertTrue(pack["integrity"]["pdf_sha256"])
            self.assertEqual(len(pack["integrity"]["json_sha256"]), 64)  # SHA256 hex
