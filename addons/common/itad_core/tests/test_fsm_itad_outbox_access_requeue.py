from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from ._helpers import create_test_fsm_order, create_test_location, create_test_partner


class TestFsmItadOutboxAccessRequeue(TransactionCase):
    """
    RBAC regression: only receiving managers may requeue outbox records.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_manager = cls.env.ref("itad_core.group_receiving_manager")

        cls.basic_user = cls.env["res.users"].create(
            {
                "name": "Outbox Basic User",
                "login": "outbox_basic_requeue",
                "groups_id": [(4, cls.group_user.id)],
            }
        )
        cls.manager_user = cls.env["res.users"].create(
            {
                "name": "Outbox Manager User",
                "login": "outbox_manager_requeue",
                "groups_id": [(4, cls.group_user.id), (4, cls.group_manager.id)],
            }
        )

        partner = create_test_partner(cls.env, name="Outbox Requeue Partner")
        location = create_test_location(cls.env, partner, name="Outbox Requeue Location")
        team = location.team_id
        if "member_ids" in team._fields:
            team.write({"member_ids": [(4, cls.basic_user.id), (4, cls.manager_user.id)]})
        cls.order = create_test_fsm_order(cls.env, location, name="OUTBOX-REQUEUE")

        cls.outbox = cls.env["itad.core.outbox"].create(
            {
                "order_id": cls.order.id,
                "payload_json": "{}",
                "state": "dead_letter",
                "attempt_count": 2,
                "last_error": "fail",
                "last_http_status": 500,
                "dead_letter_reason": "max_attempts_exceeded",
            }
        )

    def test_basic_user_cannot_requeue(self):
        with self.assertRaises(AccessError):
            self.outbox.with_user(self.basic_user).action_requeue()

    def test_manager_can_requeue(self):
        result = self.outbox.with_user(self.manager_user).action_requeue()
        self.assertTrue(result)
        self.assertEqual(self.outbox.state, "pending")
        self.assertEqual(self.outbox.attempt_count, 0)
        self.assertFalse(self.outbox.dead_letter_reason)
        self.assertFalse(self.outbox.last_http_status)
        self.assertTrue(self.outbox.next_retry_at)
        self.assertEqual(self.outbox.order_id.itad_submit_state, "pending")
