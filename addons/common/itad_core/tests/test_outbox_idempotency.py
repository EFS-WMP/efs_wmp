from odoo.tests.common import SavepointCase


class TestOutboxIdempotency(SavepointCase):
    def test_submit_reuses_outbox_row(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.env.ref("fieldservice.test_location").id,
                "stage_id": self.env.ref("fieldservice.fsm_stage_completed").id,
            }
        )
        order.action_submit_pickup_manifest()
        order.action_submit_pickup_manifest()

        outbox = self.env["itad.core.outbox"].search([("order_id", "=", order.id)])
        self.assertEqual(len(outbox), 1)
        self.assertTrue(outbox.idempotency_key)
        self.assertTrue(outbox.correlation_id)
        self.assertEqual(order.itad_outbox_id.id, outbox.id)
