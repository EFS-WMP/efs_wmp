from odoo.tests.common import TransactionCase

from ._helpers import create_test_fsm_order, create_test_location, create_test_partner


class TestFsmItadOutboxAccessBasic(TransactionCase):
    """
    Regression test: basic internal users should be allowed to create outbox rows.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.basic_user = cls.env["res.users"].create(
            {
                "name": "Outbox Basic User",
                "login": "outbox_basic_user",
                "groups_id": [(4, cls.group_user.id)],
            }
        )

        partner = create_test_partner(cls.env, name="Outbox Basic Partner")
        location = create_test_location(cls.env, partner, name="Outbox Basic Location")
        # Ensure team membership so record rules on FSM orders do not block read access
        team = location.team_id
        if "member_ids" in team._fields:
            team.write({"member_ids": [(4, cls.basic_user.id)]})
        cls.order = create_test_fsm_order(cls.env, location, name="OUTBOX-BASIC")

    def test_basic_user_can_create_outbox(self):
        outbox_model = self.env["itad.core.outbox"].with_user(self.basic_user)
        outbox = outbox_model.create(
            {
                "order_id": self.order.id,
                "payload_json": '{"foo":"bar"}',
            }
        )

        self.assertTrue(outbox)
        self.assertEqual(outbox.order_id.id, self.order.id)
        self.assertEqual(outbox.create_uid, self.basic_user)
        self.assertTrue(outbox.idempotency_key)
        self.assertTrue(outbox.correlation_id)
        self.assertEqual(outbox.payload_sha256, "9e6e661541d44a1bc94a4f7f994a586287a317dc0c166261992f05b2b5cbaf42")
