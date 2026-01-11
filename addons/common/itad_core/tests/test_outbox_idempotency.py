import uuid

from odoo.tests.common import TransactionCase


class TestOutboxIdempotency(TransactionCase):
    def test_submit_reuses_outbox_row(self):
        partner = self.env["res.partner"].create(
            {"name": f"Test Partner {uuid.uuid4().hex[:8]}", "is_company": True}
        )
        team = self.env["fsm.team"].create({"name": f"Test Team {uuid.uuid4().hex[:8]}", "sequence": 99})
        location = self.env["fsm.location"].create(
            {
                "name": partner.name,
                "partner_id": partner.id,
                "owner_id": partner.id,
                "team_id": team.id,
            }
        )
        existing_stage = self.env["fsm.stage"].search(
            [("stage_type", "=", "order")], order="sequence desc", limit=1
        )
        sequence = (existing_stage.sequence if existing_stage else 0) + 1
        stage_completed = self.env["fsm.stage"].create(
            {
                "name": f"Completed {sequence}",
                "stage_type": "order",
                "sequence": sequence,
                "is_closed": True,
            }
        )
        order = self.env["fsm.order"].create(
            {
                "location_id": location.id,
                "stage_id": stage_completed.id,
            }
        )
        order.action_submit_pickup_manifest()
        order.action_submit_pickup_manifest()

        outbox = self.env["itad.core.outbox"].search([("order_id", "=", order.id)])
        self.assertEqual(len(outbox), 1)
        self.assertTrue(outbox.idempotency_key)
        self.assertTrue(outbox.correlation_id)
        self.assertEqual(order.itad_outbox_id.id, outbox.id)
