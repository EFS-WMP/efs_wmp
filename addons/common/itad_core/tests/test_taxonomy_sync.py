# File: itad_core/tests/test_taxonomy_sync.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo import fields
import json


class TestTaxonomySync(TransactionCase):
    """Phase 2.3: Tests for material taxonomy sync engine"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sync_service = cls.env["itad.material.sync"]
        cls.cache_model = cls.env["itad.material.type.cache"]
        cls.sync_state_model = cls.env["itad.taxonomy.sync.state"]

    def _mock_itad_response(self, items):
        """Helper to create mock ITAD Core API response in wrapper format"""
        return {
            "items": items,
            "meta": {
                "generated_at": "2026-01-17T20:00:00Z",
                "count": len(items),
                "include_inactive": True,
                "updated_since": None,
            }
        }

    @patch("odoo.addons.itad_core.models.itad_material_sync.requests.get")
    def test_taxonomy_sync_creates_records_first_run(self, mock_get):
        """Test first sync creates records from ITAD Core response"""
        # Mock response with 2 material types
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._mock_itad_response([
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "code": "BAT-LI-001",
                "name": "Lithium Batteries",
                "stream": "batteries",
                "hazard_class": "Class 9",
                "default_action": "recycle",
                "requires_photo": True,
                "requires_weight": True,
                "is_active": True,
                "updated_at": "2026-01-17T18:00:00Z",
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "code": "EW-CPU-001",
                "name": "CPU/Boards",
                "stream": "electronics",
                "hazard_class": None,
                "default_action": "recycle",
                "requires_photo": False,
                "requires_weight": True,
                "is_active": True,
                "updated_at": "2026-01-17T19:00:00Z",
            },
        ])
        mock_get.return_value = mock_response

        # Run sync
        result = self.sync_service._sync_from_itad_core(manual=True)

        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["stats"]["created"], 2)

        # Verify records created
        cache_records = self.cache_model.search([])
        self.assertEqual(len(cache_records), 2)

        # Verify first record
        bat = cache_records.filtered(lambda r: r.code == "BAT-LI-001")
        self.assertEqual(bat.name, "Lithium Batteries")
        self.assertEqual(bat.stream, "batteries")
        self.assertTrue(bat.requires_photo)
        self.assertTrue(bat.requires_weight)
        self.assertTrue(bat.active)

    @patch("odoo.addons.itad_core.models.itad_material_sync.requests.get")
    def test_taxonomy_sync_is_idempotent_no_duplicates(self, mock_get):
        """Test running sync twice does not create duplicates"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._mock_itad_response([
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "code": "TEST-001",
                "name": "Test Material",
                "stream": "test",
                "hazard_class": None,
                "default_action": None,
                "requires_photo": False,
                "requires_weight": True,
                "is_active": True,
                "updated_at": "2026-01-17T20:00:00Z",
            },
        ])
        mock_get.return_value = mock_response

        # Run sync first time
        self.sync_service._sync_from_itad_core(manual=True)
        count_first = self.cache_model.search_count([])

        # Run sync second time
        self.sync_service._sync_from_itad_core(manual=True)
        count_second = self.cache_model.search_count([])

        # Should have same count (no duplicates)
        self.assertEqual(count_first, count_second)

        # Verify unique by itad_core_uuid
        records = self.cache_model.search([("code", "=", "TEST-001")])
        self.assertEqual(len(records), 1)

    @patch("odoo.addons.itad_core.models.itad_material_sync.requests.get")
    def test_taxonomy_sync_deactivates_inactive(self, mock_get):
        """Test sync sets active=False when is_active=False from ITAD Core"""
        # First sync with active record
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._mock_itad_response([
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "code": "DEACT-001",
                "name": "To Be Deactivated",
                "stream": "test",
                "hazard_class": None,
                "default_action": None,
                "requires_photo": False,
                "requires_weight": False,
                "is_active": True,
                "updated_at": "2026-01-17T18:00:00Z",
            },
        ])
        mock_get.return_value = mock_response

        self.sync_service._sync_from_itad_core(manual=True)

        # Verify active
        record = self.cache_model.search([("code", "=", "DEACT-001")])
        self.assertTrue(record.active)

        # Second sync with inactive record
        mock_response.json.return_value = self._mock_itad_response([
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",  # Same UUID
                "code": "DEACT-001",
                "name": "To Be Deactivated",
                "stream": "test",
                "hazard_class": None,
                "default_action": None,
                "requires_photo": False,
                "requires_weight": False,
                "is_active": False,  # Now inactive
                "updated_at": "2026-01-17T19:00:00Z",
            },
        ])

        result = self.sync_service._sync_from_itad_core(manual=True)

        # Verify deactivated
        record = self.cache_model.search([("code", "=", "DEACT-001")])
        self.assertFalse(record.active)
        self.assertEqual(result["stats"]["deactivated"], 1)

    @patch("odoo.addons.itad_core.models.itad_material_sync.requests.get")
    def test_sync_validates_contract_wrapper(self, mock_get):
        """SECURITY: Test sync fails if response missing items or meta"""
        # Mock response missing 'meta'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}  # Missing 'meta'
        mock_get.return_value = mock_response

        result = self.sync_service._sync_from_itad_core(manual=True)

        # Should fail with contract error
        self.assertFalse(result["success"])
        self.assertIn("missing 'items' or 'meta'", result["error"].lower())

    @patch("odoo.addons.itad_core.models.itad_material_sync.requests.get")
    def test_sync_validates_contract_item_fields(self, mock_get):
        """SECURITY: Test sync fails if item missing required fields"""
        # Mock response with incomplete item
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._mock_itad_response([
            {"id": "uuid-123"}  # Missing code, name, stream, requires_*, etc.
        ])
        mock_get.return_value = mock_response

        result = self.sync_service._sync_from_itad_core(manual=True)

        # Should fail with missing fields error
        self.assertFalse(result["success"])
        self.assertIn("missing required fields", result["error"].lower())

    def test_deterministic_advisory_lock_key(self):
        """SECURITY: Test advisory lock key is stable and deterministic"""
        namespace = "itad_core.material_type_sync"
        key1 = self.sync_service._advisory_lock_key(namespace)
        key2 = self.sync_service._advisory_lock_key(namespace)

        # Should be same across calls
        self.assertEqual(key1, key2)
        self.assertIsInstance(key1, int)
        self.assertGreater(key1, 0)  # Positive int

        # Different namespace should produce different key
        key3 = self.sync_service._advisory_lock_key("different.namespace")
        self.assertNotEqual(key1, key3)
