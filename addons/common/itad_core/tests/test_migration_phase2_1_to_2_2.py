# File: itad_core/tests/test_migration_phase2_1_to_2_2.py

from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo import fields
import uuid
from odoo.addons.itad_core.scripts.migrate_phase2_1_to_2_2 import migrate_legacy_receipts
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestMigrationPhase21To22(TransactionCase):
    """Test backward compatibility migration for Phase 2.1 -> 2.2"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)

    def _fetch_idempotency_key(self, order_id):
        self.env.cr.execute(
            "SELECT itad_receipt_idempotency_key FROM fsm_order WHERE id = %s",
            [order_id],
        )
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def test_migration_dry_run_no_changes(self):
        """Test dry-run mode makes no changes"""
        # Create legacy exception record
        order = create_test_fsm_order(self.env, self.test_location, **{
            "name": "TEST-LEGACY-001",
            "itad_pickup_manifest_id": "legacy-manifest-001",
            "itad_manifest_no": "MAN-2026-111111",
            "itad_bol_id": "BOL-2026-001111",
            "itad_receipt_state": "exception",
        })
        
        # Run dry-run migration
        result = migrate_legacy_receipts(self.env, dry_run=True)
        
        # Verify no changes
        self.assertFalse(self._fetch_idempotency_key(order.id))
        
        # Verify report
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["eligible"], 1)
        self.assertEqual(result["fixed"], 0)

    def test_migration_apply_generates_deterministic_key(self):
        """Test apply mode generates deterministic idempotency key"""
        # Create legacy exception record with stable data
        order = create_test_fsm_order(self.env, self.test_location, **{
            "name": "TEST-LEGACY-002",
            "itad_pickup_manifest_id": "legacy-manifest-002",
            "itad_manifest_no": "MAN-2026-222222",
            "itad_bol_id": "BOL-2026-002222",
            "itad_receipt_state": "exception",
        })
        
        # Run migration
        result = migrate_legacy_receipts(self.env, dry_run=False)
        
        # Verify key was generated
        order_key = self._fetch_idempotency_key(order.id)
        self.assertTrue(order_key)
        self.assertTrue(order_key.startswith("receipt-"))
        
        # Verify determinism: same inputs = same key
        expected_namespace = uuid.UUID("00000000-0000-0000-0000-000000000222")
        name_str = f"fsm.order:{order.id}:{order.itad_bol_id}:{order.itad_manifest_no}"
        expected_key = f"receipt-{uuid.uuid5(expected_namespace, name_str)}"
        self.assertEqual(order_key, expected_key)
        
        # Verify report
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["eligible"], 1)
        self.assertEqual(result["fixed"], 1)

    def test_migration_idempotent(self):
        """Test running migration twice produces same result"""
        order = create_test_fsm_order(self.env, self.test_location, **{
            "name": "TEST-LEGACY-003",
            "itad_pickup_manifest_id": "legacy-manifest-003",
            "itad_manifest_no": "MAN-2026-333333",
            "itad_bol_id": "BOL-2026-003333",
            "itad_receipt_state": "exception",
        })
        
        # First run
        result1 = migrate_legacy_receipts(self.env, dry_run=False)
        key_after_first = self._fetch_idempotency_key(order.id)
        
        # Second run
        result2 = migrate_legacy_receipts(self.env, dry_run=False)
        key_after_second = self._fetch_idempotency_key(order.id)
        
        # Keys should be identical
        self.assertEqual(key_after_first, key_after_second)
        
        # Second run should show 0 fixed (already migrated)
        self.assertEqual(result1["fixed"], 1)
        self.assertEqual(result2["fixed"], 0)

    def test_migration_skips_received_records(self):
        """Test migration skips successfully received records"""
        order = create_test_fsm_order(self.env, self.test_location, **{
            "name": "TEST-RECEIVED-001",
            "itad_pickup_manifest_id": "received-manifest-001",
            "itad_manifest_no": "MAN-2026-444444",
            "itad_bol_id": "BOL-2026-004444",
            "itad_receipt_state": "received",
            "itad_receipt_confirmed_at": fields.Datetime.now(),
        })
        
        # Run migration
        result = migrate_legacy_receipts(self.env, dry_run=False)
        
        # Verify not migrated (already successful)
        self.assertFalse(self._fetch_idempotency_key(order.id))
        
        # Should be scanned but not eligible
        self.assertGreaterEqual(result["scanned"], 1)
        self.assertEqual(result["eligible"], 0)

    def test_migration_skips_existing_key(self):
        """Test migration preserves existing idempotency keys"""
        existing_key = "receipt-existing-manual-key"
        order = create_test_fsm_order(self.env, self.test_location, **{
            "name": "TEST-EXISTING-KEY",
            "itad_pickup_manifest_id": "existing-manifest-001",
            "itad_manifest_no": "MAN-2026-555555",
            "itad_bol_id": "BOL-2026-005555",
            "itad_receipt_state": "exception",
            "itad_receipt_idempotency_key": existing_key,
        })
        
        # Run migration
        result = migrate_legacy_receipts(self.env, dry_run=False)
        
        # Verify key unchanged
        self.assertEqual(self._fetch_idempotency_key(order.id), existing_key)
        
        # Should be scanned but not fixed (already has key)
        self.assertEqual(result["fixed"], 0)
