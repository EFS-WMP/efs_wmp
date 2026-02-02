import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.itad_core.tests._helpers import (
    create_test_fsm_order,
    create_test_location,
    create_test_partner,
)


class TestOutboxBackoff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        icp = cls.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.outbox_backoff_base_seconds", "120")
        icp.set_param("itad_core.outbox_backoff_jitter_ratio", "0.25")
        icp.set_param("itad_core.outbox_max_delay_seconds", "600")

    def _create_outbox(self):
        partner = create_test_partner(self.env, name="CI Backoff Partner")
        location = create_test_location(self.env, partner, name="CI Backoff Location")
        order = create_test_fsm_order(self.env, location, name="CI-BACKOFF-ORDER")
        return self.env["itad.core.outbox"].create(
            {
                "order_id": order.id,
                "payload_json": "{}",
                "idempotency_key": "ci-backoff-key",
            }
        )

    def test_backoff_uses_deterministic_jitter(self):
        outbox = self._create_outbox()
        fixed_now = datetime(2026, 2, 2, 12, 0, 0)

        attempt = 1
        base_delay = 120
        jitter_range = int(base_delay * 0.25)
        digest = hashlib.sha256(f"{outbox.idempotency_key}:{attempt}".encode("utf-8")).hexdigest()
        jitter = int(digest, 16) % (jitter_range + 1)
        expected_delay = base_delay + jitter

        with patch("odoo.fields.Datetime.now", return_value=fixed_now):
            next_retry = outbox._compute_next_retry_at(attempt)

        delta = (next_retry - fixed_now).total_seconds()
        self.assertEqual(delta, expected_delay)
