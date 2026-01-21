# File: itad_core/tests/test_receiving_audit_archiving.py

from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import timedelta
from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestReceivingAuditArchiving(TransactionCase):
    """Test audit log archiving cron"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_partner = create_test_partner(cls.env)
        cls.test_location = create_test_location(cls.env, cls.test_partner)
        cls.test_order = create_test_fsm_order(cls.env, cls.test_location, **{
            "name": "TEST-ORDER-ARCHIVE",
            "itad_pickup_manifest_id": "test-manifest-archive",
            "itad_manifest_no": "MAN-2026-666666",
            "itad_bol_id": "BOL-2026-000666",
        })
        
        cls.test_user = cls.env.ref("base.user_admin")

    def _fetch_archive_state(self, log_id):
        self.env.cr.execute(
            "SELECT archived, archived_at FROM itad_receipt_audit_log WHERE id = %s",
            [log_id],
        )
        row = self.env.cr.fetchone()
        return row[0], row[1]

    def test_archive_old_logs(self):
        """Test archiving logs older than retention period"""
        # Set retention to 180 days
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.audit_retention_days", "180"
        )
        
        now = fields.Datetime.now()
        
        # Create old log (200 days ago - should be archived)
        old_log = self.env["itad.receipt.audit.log"].create({
            "order_id": self.test_order.id,
            "user_id": self.test_user.id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "success": True,
            "outcome": "SUCCESS",
            "attempt_number": 1,
            "attempted_at": now - timedelta(days=200),
        })
        
        # Create recent log (30 days ago - should NOT be archived)
        recent_log = self.env["itad.receipt.audit.log"].create({
            "order_id": self.test_order.id,
            "user_id": self.test_user.id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "success": True,
            "outcome": "SUCCESS",
            "attempt_number": 2,
            "attempted_at": now - timedelta(days=30),
        })

        # Run archiving cron
        AuditLogModel = self.env["itad.receipt.audit.log"]
        AuditLogModel._cron_archive_old_receipt_audit_logs()
        
        # Verify old log is archived
        archived, archived_at = self._fetch_archive_state(old_log.id)
        self.assertTrue(archived)
        self.assertIsNotNone(archived_at)
        
        # Verify recent log is NOT archived
        archived, archived_at = self._fetch_archive_state(recent_log.id)
        self.assertFalse(archived)
        self.assertFalse(archived_at)

    def test_archive_does_not_rearchive(self):
        """Test archiving does not update already archived logs"""
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.audit_retention_days", "180"
        )
        
        now = fields.Datetime.now()
        first_archive_time = now - timedelta(days=10)
        
        # Create already archived log
        archived_log = self.env["itad.receipt.audit.log"].create({
            "order_id": self.test_order.id,
            "user_id": self.test_user.id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "success": True,
            "outcome": "SUCCESS",
            "attempt_number": 1,
            "attempted_at": now - timedelta(days=200),
            "archived": True,
            "archived_at": first_archive_time,
        })
        
        AuditLogModel = self.env["itad.receipt.audit.log"]
        AuditLogModel._cron_archive_old_receipt_audit_logs()
        
        # Verify archived_at did NOT change
        _, archived_at = self._fetch_archive_state(archived_log.id)
        self.assertEqual(archived_at, first_archive_time)

    def test_archive_with_custom_retention(self):
        """Test archiving respects custom retention period"""
        # Set retention to 30 days
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.audit_retention_days", "30"
        )
        
        now = fields.Datetime.now()
        
        # Create log 45 days old (should be archived with 30-day retention)
        old_log = self.env["itad.receipt.audit.log"].create({
            "order_id": self.test_order.id,
            "user_id": self.test_user.id,
            "manifest_no": self.test_order.itad_manifest_no,
            "bol_id": self.test_order.itad_bol_id,
            "success": True,
            "outcome": "SUCCESS",
            "attempt_number": 1,
            "attempted_at": now - timedelta(days=45),
        })
        
        AuditLogModel = self.env["itad.receipt.audit.log"]
        AuditLogModel._cron_archive_old_receipt_audit_logs()
        
        archived, _ = self._fetch_archive_state(old_log.id)
        self.assertTrue(archived)
