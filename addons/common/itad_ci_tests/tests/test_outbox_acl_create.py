from odoo.tests.common import TransactionCase

from odoo.exceptions import AccessError

from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestOutboxAclCreate(TransactionCase):
    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref("base.group_user")
        self.basic_user = self.env["res.users"].create(
            {
                "name": "CI Outbox Basic",
                "login": "ci_outbox_basic",
                "groups_id": [(4, self.group_user.id)],
            }
        )
        partner = create_test_partner(self.env, name="CI Outbox Partner")
        location = create_test_location(self.env, partner, name="CI Outbox Location")
        team = location.team_id
        if "member_ids" in team._fields:
            team.write({"member_ids": [(4, self.basic_user.id)]})
        self.order = create_test_fsm_order(self.env, location, name="CI-OUTBOX-ORDER")

    def test_basic_user_can_create_outbox(self):
        outbox_model = self.env["itad.core.outbox"].with_user(self.basic_user)
        record = outbox_model.create(
            {
                "order_id": self.order.id,
                "payload_json": "{}",
            }
        )
        self.assertTrue(record.id)
        self.assertEqual(record.create_uid, self.basic_user)
        self.assertTrue(record.idempotency_key)
        self.assertTrue(record.correlation_id)
        self.assertTrue(record.payload_sha256)

    def test_basic_user_write_denied(self):
        outbox_model = self.env["itad.core.outbox"].with_user(self.basic_user)
        record = outbox_model.create({"order_id": self.order.id, "payload_json": "{}"})
        with self._assertRaises((AccessError,)):
            outbox_model.browse(record.id).write({"state": "sent"})
