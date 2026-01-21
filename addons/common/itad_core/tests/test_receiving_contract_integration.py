# File: itad_core/tests/test_receiving_contract_integration.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo import fields
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestReceivingContractIntegration(TransactionCase):
    """
    Contract integration tests based on docs/phase1/INTEGRATION_CONTRACT_ODoo_ITADCore.md
    
    Validates that outgoing requests match the exact contract schema.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Contract schema extracted from INTEGRATION_CONTRACT_ODoo_ITADCore.md
        cls.REQUIRED_FIELDS = {
            "bol_id", "occurred_at", "material_received_as", "container_type",
            "quantity", "gross_weight", "tare_weight", "net_weight", "weight_unit",
            "scale_id", "ddr_status", "receiver_employee_id", "receiver_name",
            "receiver_signature_json", "tare_source"
        }
        
        cls.OPTIONAL_FIELDS = {"notes"}
        
        cls.FORBIDDEN_FIELDS = {"id", "created_at", "updated_at", "created_by"}
        
        cls.REQUIRED_HEADERS = ["Idempotency-Key", "X-Correlation-Id", "Content-Type"]

        # Create test order
        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
        cls.test_order = create_test_fsm_order(cls.env, cls.test_location, **{
            "name": "TEST-ORDER-CONTRACT",
            "itad_pickup_manifest_id": "test-manifest-contract",
            "itad_manifest_no": "MAN-2026-999999",
            "itad_bol_id": "BOL-2026-000999",
            "itad_receipt_state": "pending",
        })
        
        # Create receiving manager user
        cls.group_receiving_manager = cls.env.ref("itad_core.group_receiving_manager")
        cls.group_fsm_dispatcher = cls.env.ref("fieldservice.group_fsm_dispatcher")
        cls.test_user = cls.env["res.users"].create({
            "name": "Contract Test User",
            "login": "contract_test",
            "groups_id": [
                (4, cls.group_receiving_manager.id),
                (4, cls.group_fsm_dispatcher.id),
            ],
        })

    def _create_wizard(self):
        """Helper to create wizard with valid data"""
        return self.env["itad.receiving.wizard"].with_user(self.test_user).create({
            "fsm_order_id": self.test_order.id,
            "pickup_manifest_id": self.test_order.itad_pickup_manifest_id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "material_type_code": "EW-CPU-001",
            "actual_weight_lbs": 150.5,
            "operator_notes": "Test notes",
        })

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_contract_request_has_all_required_fields(self, mock_get, mock_post):
        """Test outgoing payload contains all required fields per contract"""
        # Mock health check
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        
        # Mock successful POST
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-test-123", "bol_id": self.test_order.itad_bol_id}
        )
        
        wizard = self._create_wizard()
        wizard.action_confirm_receipt()
        
        # Extract actual payload sent
        call_args = mock_post.call_args
        actual_payload = call_args[1]["json"]
        
        # Verify all required fields present
        for field_name in self.REQUIRED_FIELDS:
            self.assertIn(field_name, actual_payload, f"Missing required field: {field_name}")

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_contract_request_has_no_forbidden_fields(self, mock_get, mock_post):
        """Test outgoing payload does NOT contain forbidden fields"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-test-456"}
        )
        
        wizard = self._create_wizard()
        wizard.action_confirm_receipt()
        
        actual_payload = mock_post.call_args[1]["json"]
        
        # Verify no forbidden fields
        for forbidden_field in self.FORBIDDEN_FIELDS:
            self.assertNotIn(forbidden_field, actual_payload,
                           f"Forbidden field found in payload: {forbidden_field}")

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_contract_request_headers(self, mock_get, mock_post):
        """Test request includes required headers per contract"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-test-789"}
        )
        
        wizard = self._create_wizard()
        wizard.action_confirm_receipt()
        
        actual_headers = mock_post.call_args[1]["headers"]
        
        # Verify required headers
        for header in self.REQUIRED_HEADERS:
            self.assertIn(header, actual_headers, f"Missing required header: {header}")
        
        # Verify Idempotency-Key format
        self.assertTrue(actual_headers["Idempotency-Key"].startswith("receipt-"))
        
        # Verify X-Correlation-Id format
        self.assertTrue(actual_headers["X-Correlation-Id"].startswith("corr-receipt-"))

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_contract_receiver_signature_json_structure(self, mock_get, mock_post):
        """Test receiver_signature_json matches contract structure"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-test-sig"}
        )
        
        wizard = self._create_wizard()
        wizard.action_confirm_receipt()
        
        actual_payload = mock_post.call_args[1]["json"]
        signature = actual_payload["receiver_signature_json"]
        
        # Verify signature structure per contract
        self.assertIn("type", signature)
        self.assertIn("user_id", signature)
        self.assertIn("timestamp", signature)
        self.assertIsInstance(signature["type"], str)
        self.assertIsInstance(signature["user_id"], int)
        self.assertIsInstance(signature["timestamp"], str)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_contract_numeric_types(self, mock_get, mock_post):
        """Test numeric fields have correct types per contract"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-test-numeric"}
        )
        
        wizard = self._create_wizard()
        wizard.action_confirm_receipt()
        
        actual_payload = mock_post.call_args[1]["json"]
        
        # Verify quantity is int
        self.assertIsInstance(actual_payload["quantity"], int)
        
        # Verify weights are numeric (int or float)
        self.assertIsInstance(actual_payload["gross_weight"], (int, float))
        self.assertIsInstance(actual_payload["net_weight"], (int, float))
        self.assertIsInstance(actual_payload["tare_weight"], (int, float))
        
        # Verify constraints
        self.assertGreater(actual_payload["gross_weight"], 0)
        self.assertGreater(actual_payload["net_weight"], 0)
        self.assertGreaterEqual(actual_payload["tare_weight"], 0)
        self.assertGreater(actual_payload["quantity"], 0)

    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.post")
    @patch("odoo.addons.itad_core.models.itad_receiving_wizard.requests.get")
    def test_contract_no_extra_fields(self, mock_get, mock_post):
        """Test payload contains only allowed fields (no extras)"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "healthy"})
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "rwrec-test-extra"}
        )
        
        wizard = self._create_wizard()
        wizard.action_confirm_receipt()
        
        actual_payload = mock_post.call_args[1]["json"]
        allowed_fields = self.REQUIRED_FIELDS | self.OPTIONAL_FIELDS
        
        # Verify no extra fields
        for field_name in actual_payload.keys():
            self.assertIn(field_name, allowed_fields,
                         f"Extra field not in contract: {field_name}")
