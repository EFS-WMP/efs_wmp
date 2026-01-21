# File: itad_core/tests/test_taxonomy_security.py

from unittest.mock import Mock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields


class TestTaxonomySecurity(TransactionCase):
    """Phase 2.3 Security: Tests for ACL enforcement and break-glass auditing"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cache_model = cls.env["itad.material.type.cache"]
        cls.audit_model = cls.env["itad.taxonomy.audit.log"]
        
        # Create test groups
        cls.group_integration = cls.env.ref("itad_core.group_itad_integration")
        cls.group_receiving = cls.env.ref("itad_core.group_receiving_manager")
        
        # Create test users
        cls.user_no_group = cls.env["res.users"].create({
            "name": "User No Group",
            "login": "user_no_group_test",
            "groups_id": [(4, cls.env.ref("base.group_user").id)],
        })
        
        cls.user_integration = cls.env["res.users"].create({
            "name": "Integration User",
            "login": "user_integration_test",
            "groups_id": [
                (4, cls.env.ref("base.group_user").id),
                (4, cls.group_integration.id),
            ],
        })
        
        cls.user_receiving = cls.env["res.users"].create({
            "name": "Receiving Manager",
            "login": "user_receiving_test",
            "groups_id": [
                (4, cls.env.ref("base.group_user").id),
                (4, cls.group_receiving.id),
            ],
        })

    def test_cache_rejects_write_without_integration_group(self):
        """Test cache model blocks write even with context flag if user lacks group"""
        # User without integration group tries to create with context flag
        with self.assertRaises(UserError) as ctx:
            self.cache_model.with_user(self.user_no_group).with_context(itad_sync=True).create({
                "itad_core_uuid": "test-uuid-123",
                "code": "TEST-001",
                "name": "Test Material",
                "stream": "test",
                "requires_photo": False,
                "requires_weight": False,
                "active": True,
            })
        
        self.assertIn("read-only", str(ctx.exception).lower())

    def test_cache_rejects_write_receiving_manager(self):
        """Test receiving manager cannot create cache records"""
        with self.assertRaises(UserError) as ctx:
            self.cache_model.with_user(self.user_receiving).create({
                "itad_core_uuid": "test-uuid-456",
                "code": "TEST-002",
                "name": "Test Material 2",
                "stream": "test",
                "requires_photo": False,
                "requires_weight": False,
                "active": True,
            })
        
        self.assertIn("read-only", str(ctx.exception).lower())

    def test_cache_allows_write_with_sudo_and_integration_group(self):
        """Test sync works with sudo() and integration group"""
        # Create record as integration user with sudo
        record = self.cache_model.sudo().with_user(self.user_integration).create({
            "itad_core_uuid": "test-uuid-789",
            "code": "TEST-003",
            "name": "Test Material 3",
            "stream": "test",
            "requires_photo": False,
            "requires_weight": False,
            "active": True,
        })
        
        self.assertTrue(record)
        self.assertEqual(record.code, "TEST-003")

    def test_cache_allows_write_as_superuser(self):
        """Test superuser can write without integration group"""
        # Admin/superuser should work
        record = self.cache_model.sudo().create({
            "itad_core_uuid": "test-uuid-admin",
            "code": "TEST-ADMIN",
            "name": "Test Admin Material",
            "stream": "test",
            "requires_photo": False,
            "requires_weight": False,
            "active": True,
        })
        
        self.assertTrue(record)

    def test_audit_log_creation(self):
        """Test audit log helper method works"""
        audit_record = self.audit_model.log_event(
            action="sync_attempt",
            details="Test sync attempt",
            success=True,
        )
        
        self.assertTrue(audit_record)
        self.assertEqual(audit_record.action, "sync_attempt")
        self.assertEqual(audit_record.user_id, self.env.user)
        self.assertTrue(audit_record.occurred_at)

    def test_break_glass_audit_event_created(self):
        """Test break-glass usage creates audit event"""
        # This would be called by wizard during stale override
        audit_record = self.audit_model.log_event(
            action="stale_override_used",
            details="Break-glass override for stale taxonomy",
            success=True,
        )
        
        self.assertTrue(audit_record)
        self.assertEqual(audit_record.action, "stale_override_used")
        self.assertTrue(audit_record.success)

    def test_audit_log_tracks_failures(self):
        """Test audit log captures failure events"""
        audit_record = self.audit_model.log_event(
            action="sync_failure",
            details="Lock acquisition failed",
            success=False,
            error_message="Could not acquire advisory lock",
        )
        
        self.assertTrue(audit_record)
        self.assertFalse(audit_record.success)
        self.assertIn("lock", audit_record.error_message.lower())

    def test_context_flag_not_sufficient_for_permission(self):
        """SECURITY CRITICAL: Context flag alone should NOT bypass permission"""
        # Even with context flag, user without group should be blocked
        with self.assertRaises(UserError):
            self.cache_model.with_user(self.user_no_group).with_context(
                itad_sync=True,  # Context flag present but should be ignored
                force_write=True,  # Even extra flags shouldn't help
            ).create({
                "itad_core_uuid": "hack-attempt-uuid",
                "code": "HACK-001",
                "name": "Hack Attempt",
                "stream": "test",
                "requires_photo": False,
                "requires_weight": False,
                "active": True,
            })
        
        # Verify no record was created
        self.assertEqual(
            self.cache_model.search_count([("code", "=", "HACK-001")]),
            0
        )
