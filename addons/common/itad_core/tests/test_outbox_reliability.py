from unittest.mock import Mock, patch

from odoo import fields
from odoo.tests.common import TransactionCase

from ._helpers import create_test_fsm_order, create_test_location, create_test_partner


class TestOutboxReliability(TransactionCase):
    """Phase 2.5: Outbox retry/backoff + DLQ reliability tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_receiving = cls.env.ref("itad_core.group_receiving_manager")
        cls.user_receiving = cls.env["res.users"].create(
            {
                "name": "Receiving Manager Outbox",
                "login": "user_receiving_outbox",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.group_receiving.id),
                ],
            }
        )
        icp = cls.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.outbox_max_attempts", "3")
        icp.set_param("itad_core.outbox_backoff_base_seconds", "60")
        icp.set_param("itad_core.outbox_max_delay_seconds", "600")
        icp.set_param("itad_core.outbox_backoff_jitter_ratio", "0.25")

    def _create_order(self):
        partner = create_test_partner(self.env, name="Outbox Partner")
        location = create_test_location(self.env, partner, name="Outbox Location")
        return create_test_fsm_order(self.env, location, name="OUTBOX-ORDER")

    def _create_outbox(self, order):
        return self.env["itad.core.outbox"].create(
            {
                "order_id": order.id,
                "idempotency_key": "outbox-idempotency",
                "correlation_id": "outbox-correlation",
                "payload_json": "{}",
                "payload_sha256": "deadbeef",
            }
        )

    @patch("odoo.addons.itad_core.models.itad_outbox.requests.post")
    def test_retry_backoff_sets_next_retry_at(self, mock_post):
        order = self._create_order()
        outbox = self._create_outbox(order)

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        before = fields.Datetime.now()
        outbox._process_one()

        self.assertEqual(outbox.state, "failed")
        self.assertEqual(outbox.attempt_count, 1)
        self.assertEqual(outbox.last_http_status, 500)
        self.assertFalse(outbox.dead_letter_reason)
        self.assertTrue(outbox.next_retry_at)
        delta_seconds = (outbox.next_retry_at - before).total_seconds()
        self.assertGreaterEqual(delta_seconds, 60)
        self.assertLessEqual(delta_seconds, 75)

    @patch("odoo.addons.itad_core.models.itad_outbox.requests.post")
    def test_non_retryable_status_moves_to_dead_letter(self, mock_post):
        order = self._create_order()
        outbox = self._create_outbox(order)

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        outbox._process_one()

        self.assertEqual(outbox.state, "dead_letter")
        self.assertEqual(outbox.attempt_count, 1)
        self.assertEqual(outbox.last_http_status, 400)
        self.assertEqual(outbox.dead_letter_reason, "non_retryable_status:400")
        self.assertFalse(outbox.next_retry_at)

    @patch("odoo.addons.itad_core.models.itad_outbox.requests.post")
    def test_max_attempts_moves_to_dead_letter(self, mock_post):
        order = self._create_order()
        outbox = self._create_outbox(order)
        outbox.write({"attempt_count": 2})

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        outbox._process_one()

        self.assertEqual(outbox.state, "dead_letter")
        self.assertEqual(outbox.attempt_count, 3)
        self.assertEqual(outbox.dead_letter_reason, "max_attempts_exceeded")
        self.assertFalse(outbox.next_retry_at)

    def test_requeue_resets_state_and_attempts(self):
        order = self._create_order()
        outbox = self._create_outbox(order)
        outbox.write(
            {
                "state": "dead_letter",
                "attempt_count": 2,
                "last_error": "fail",
                "last_http_status": 500,
                "dead_letter_reason": "max_attempts_exceeded",
            }
        )

        outbox.with_user(self.user_receiving).action_requeue()

        self.assertEqual(outbox.state, "pending")
        self.assertEqual(outbox.attempt_count, 0)
        self.assertFalse(outbox.dead_letter_reason)
        self.assertFalse(outbox.last_http_status)
        self.assertTrue(outbox.next_retry_at)
