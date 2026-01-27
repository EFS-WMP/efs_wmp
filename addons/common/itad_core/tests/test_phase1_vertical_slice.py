"""
Phase 1 Vertical Slice: Odoo Outbox + Cron Processing with Mocks (TDD)

Tests verify:
1. Button creates outbox with stable idempotency keys (no regeneration on retry)
2. Cron transitions PENDING → SENT and persists returned IDs
3. Cron handles FAILED with exponential backoff retry
4. Idempotency key is reused across retries (preserved)
"""
import json
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


def _create_team(env):
    return env["fsm.team"].create({"name": f"Test Team {uuid.uuid4().hex[:8]}", "sequence": 99})


def _create_location(env, team):
    partner = env["res.partner"].create(
        {"name": f"Test Partner {uuid.uuid4().hex[:8]}", "is_company": True}
    )
    return env["fsm.location"].create(
        {
            "name": partner.name,
            "partner_id": partner.id,
            "owner_id": partner.id,
            "team_id": team.id,
        }
    )


def _create_completed_stage(env):
    existing_stage = env["fsm.stage"].search(
        [("stage_type", "=", "order")], order="sequence desc", limit=1
    )
    sequence = (existing_stage.sequence if existing_stage else 0) + 1
    return env["fsm.stage"].create(
        {
            "name": f"Completed {sequence}",
            "stage_type": "order",
            "sequence": sequence,
            "is_closed": True,
        }
    )


class TestPhase1ButtonAndOutboxCreation(TransactionCase):
    """Test: Button creates outbox with stable, non-regenerating keys."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]
        cls.team = _create_team(cls.env)
        cls.location = _create_location(cls.env, cls.team)
        cls.stage_completed = _create_completed_stage(cls.env)

    def test_button_creates_outbox_pending_with_stable_keys(self):
        """
        Requirement: Clicking "Submit Pickup Manifest" button creates outbox row with stable keys.
        - idempotency_key is generated once and NOT regenerated on repeat clicks
        - correlation_id is generated once and NOT regenerated
        - order.itad_outbox_id points to the same outbox row on retry
        """
        # Create a completed FSM order
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        self.assertTrue(order.is_closed, "FSM order must be in completed state")

        # First button click
        order.action_submit_pickup_manifest()

        # Verify outbox created
        outbox_records = self.outbox_model.search([("order_id", "=", order.id)])
        self.assertEqual(len(outbox_records), 1, "Should have exactly 1 outbox row after first submit")

        outbox_1 = outbox_records[0]
        idempotency_key_1 = outbox_1.idempotency_key
        correlation_id_1 = outbox_1.correlation_id

        self.assertTrue(idempotency_key_1, "idempotency_key must be set")
        self.assertTrue(correlation_id_1, "correlation_id must be set")
        self.assertEqual(outbox_1.state, "pending", "Outbox initial state should be 'pending'")

        # Verify order references the outbox
        self.assertEqual(order.itad_outbox_id.id, outbox_1.id, "Order should reference outbox")
        self.assertEqual(order.itad_submit_state, "pending", "Order submit state should be 'pending'")

        # Second button click (idempotent, should reuse)
        order.action_submit_pickup_manifest()

        # Verify still only 1 outbox row
        outbox_records = self.outbox_model.search([("order_id", "=", order.id)])
        self.assertEqual(len(outbox_records), 1, "Should still have exactly 1 outbox after retry")

        outbox_2 = outbox_records[0]
        idempotency_key_2 = outbox_2.idempotency_key
        correlation_id_2 = outbox_2.correlation_id

        # Verify keys are the same (not regenerated)
        self.assertEqual(idempotency_key_1, idempotency_key_2,
                         "idempotency_key should NOT be regenerated on repeat click")
        self.assertEqual(correlation_id_1, correlation_id_2,
                         "correlation_id should NOT be regenerated on repeat click")
        self.assertEqual(outbox_2.id, outbox_1.id,
                         "Should reuse the same outbox row on repeat click")


class TestPhase1CronPendingToSent(TransactionCase):
    """Test: Cron transitions PENDING → SENT and persists returned IDs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]
        cls.team = _create_team(cls.env)
        cls.location = _create_location(cls.env, cls.team)
        cls.stage_completed = _create_completed_stage(cls.env)

    def test_cron_transitions_pending_to_sent_and_persists_returned_ids(self):
        """
        Requirement: Cron processes PENDING outbox records and:
        - Makes HTTP POST to ITAD Core with Idempotency-Key, X-Correlation-Id headers
        - On success (200-299), transitions outbox from PENDING → SENT
        - Persists returned IDs: pickup_manifest_id, manifest_no, bol_id, geocode_gate
        - Updates source FSM order with the same read-only IDs
        - Never regenerates idempotency_key or correlation_id
        """
        # Setup: Create and submit an order
        location = self.location
        stage_completed = self.stage_completed

        self.assertIn(
            "itad_receiving_weight_record_id",
            self.env["fsm.order"]._fields,
            "Receiving Weight Record field should exist on fsm.order",
        )

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]
        idempotency_key = outbox.idempotency_key
        correlation_id = outbox.correlation_id

        self.assertEqual(outbox.state, "pending", "Outbox should start in PENDING state")
        self.assertFalse(outbox.itad_pickup_manifest_id, "IDs should not be populated yet")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pickup_manifest_id": "pm-test-001",
            "manifest_no": "MF-2026-001",
            "bol_id": "bol-test-001",
            "geocode_gate": "AUTO_ACCEPT",
            "receiving_id": "recv-test-001",
            "receiving_weight_record_id": "rwr-test-001",
        }

        # Patch the HTTP call in outbox model
        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", return_value=mock_response):
            # Run cron (or call _process_one directly)
            outbox._process_one()

        # Refresh from DB

        # Verify state transition
        self.assertEqual(outbox.state, "sent", "Outbox should transition to SENT after successful HTTP")

        # Verify returned IDs persisted in outbox
        self.assertEqual(outbox.itad_pickup_manifest_id, "pm-test-001")
        self.assertEqual(outbox.itad_manifest_no, "MF-2026-001")
        self.assertEqual(outbox.itad_bol_id, "bol-test-001")
        self.assertEqual(outbox.itad_geocode_gate, "AUTO_ACCEPT")
        self.assertEqual(outbox.itad_receiving_id, "recv-test-001")

        # Verify source order updated with same IDs
        self.assertEqual(order.itad_pickup_manifest_id, "pm-test-001")
        self.assertEqual(order.itad_manifest_no, "MF-2026-001")
        self.assertEqual(order.itad_bol_id, "bol-test-001")
        self.assertEqual(order.itad_geocode_gate, "AUTO_ACCEPT")
        self.assertEqual(order.itad_receiving_id, "recv-test-001")
        self.assertEqual(order.itad_receiving_weight_record_id, "rwr-test-001")
        self.assertEqual(order.itad_submit_state, "sent")

        # Verify keys NOT regenerated
        self.assertEqual(outbox.idempotency_key, idempotency_key,
                         "idempotency_key should NOT change during cron processing")
        self.assertEqual(outbox.correlation_id, correlation_id,
                         "correlation_id should NOT change during cron processing")

    def test_receiving_weight_record_id_fallbacks_to_receiving_id(self):
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pickup_manifest_id": "pm-fallback-001",
            "manifest_no": "MF-2026-002",
            "bol_id": "bol-test-002",
            "geocode_gate": "AUTO_ACCEPT",
            "receiving_id": "recv-fallback-001",
        }

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", return_value=mock_response):
            outbox._process_one()

        self.assertEqual(order.itad_receiving_weight_record_id, "recv-fallback-001")
        self.assertEqual(order.itad_receiving_id, "recv-fallback-001")

    def test_manifest_fingerprint_injected_from_payload_sha256(self):
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]
        self.assertTrue(outbox.payload_sha256, "payload_sha256 should be set")

        payload_data = json.loads(outbox.payload_json)
        self.assertNotIn("manifest_fingerprint", payload_data)

        captured_payloads = []

        def mock_post(url, **kwargs):
            captured_payloads.append(kwargs.get("json"))
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "pickup_manifest_id": "pm-fingerprint-001",
                "manifest_no": "MF-2026-003",
                "bol_id": "bol-test-003",
                "geocode_gate": "AUTO_ACCEPT",
                "receiving_id": "recv-fingerprint-001",
            }
            return mock_response

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", side_effect=mock_post):
            outbox._process_one()

        self.assertTrue(captured_payloads)
        sent_payload = captured_payloads[0]
        self.assertEqual(sent_payload.get("manifest_fingerprint"), outbox.payload_sha256)

    def test_manifest_fingerprint_not_overwritten_if_present(self):
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]
        payload_data = json.loads(outbox.payload_json)
        payload_data["manifest_fingerprint"] = "pre-set"
        outbox.write({"payload_json": json.dumps(payload_data)})

        captured_payloads = []

        def mock_post(url, **kwargs):
            captured_payloads.append(kwargs.get("json"))
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "pickup_manifest_id": "pm-fingerprint-002",
                "manifest_no": "MF-2026-004",
                "bol_id": "bol-test-004",
                "geocode_gate": "AUTO_ACCEPT",
                "receiving_id": "recv-fingerprint-002",
            }
            return mock_response

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", side_effect=mock_post):
            outbox._process_one()

        self.assertTrue(captured_payloads)
        sent_payload = captured_payloads[0]
        self.assertEqual(sent_payload.get("manifest_fingerprint"), "pre-set")

    def test_retry_stability_ids_not_duplicated(self):
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pickup_manifest_id": "pm-stable-001",
            "manifest_no": "MF-2026-005",
            "bol_id": "bol-test-005",
            "geocode_gate": "AUTO_ACCEPT",
            "receiving_id": "recv-stable-001",
            "receiving_weight_record_id": "rwr-stable-001",
        }

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", return_value=mock_response):
            outbox._process_one()
            first_ids = {
                "pickup_manifest_id": order.itad_pickup_manifest_id,
                "manifest_no": order.itad_manifest_no,
                "bol_id": order.itad_bol_id,
                "receiving_id": order.itad_receiving_id,
                "receiving_weight_record_id": order.itad_receiving_weight_record_id,
            }
            outbox.write({"state": "pending"})
            outbox._process_one()

        self.assertEqual(order.itad_pickup_manifest_id, first_ids["pickup_manifest_id"])
        self.assertEqual(order.itad_manifest_no, first_ids["manifest_no"])
        self.assertEqual(order.itad_bol_id, first_ids["bol_id"])
        self.assertEqual(order.itad_receiving_id, first_ids["receiving_id"])
        self.assertEqual(order.itad_receiving_weight_record_id, first_ids["receiving_weight_record_id"])
        outbox_records = self.outbox_model.search([("order_id", "=", order.id)])
        self.assertEqual(len(outbox_records), 1)

    def test_cron_sends_correct_http_headers(self):
        """
        Requirement: HTTP request includes required headers for idempotency.
        """
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]

        # Track headers passed to HTTP call
        captured_headers = {}

        def mock_http_request(url, **kwargs):
            captured_headers.update(kwargs.get("headers", {}))
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "pickup_manifest_id": "pm-001",
                "manifest_no": "MF-001",
                "bol_id": "bol-001",
            }
            return mock_response

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", side_effect=mock_http_request):
            outbox._process_one()

        # Verify headers
        self.assertIn("Idempotency-Key", captured_headers,
                      "HTTP request must include Idempotency-Key header")
        self.assertEqual(captured_headers["Idempotency-Key"], outbox.idempotency_key)

        self.assertIn("X-Correlation-Id", captured_headers,
                      "HTTP request must include X-Correlation-Id header")
        self.assertEqual(captured_headers["X-Correlation-Id"], outbox.correlation_id)


class TestPhase1CronFailureAndRetry(TransactionCase):
    """Test: Cron handles FAILED with exponential backoff and preserves idempotency_key."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]
        cls.team = _create_team(cls.env)
        cls.location = _create_location(cls.env, cls.team)
        cls.stage_completed = _create_completed_stage(cls.env)

    def test_cron_failure_sets_failed_keeps_idempotency_key_and_retry_succeeds(self):
        """
        Requirement: On HTTP failure:
        - Outbox transitions to FAILED (not SENT)
        - idempotency_key and correlation_id are NOT regenerated
        - last_error is recorded
        - next_attempt_at is set (exponential backoff)
        - On next cron run: retry reuses same keys and succeeds
        """
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]
        idempotency_key = outbox.idempotency_key
        correlation_id = outbox.correlation_id

        # First attempt: HTTP error
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", return_value=mock_error_response):
            outbox._process_one()

        # Refresh and verify failure state
        self.assertEqual(outbox.state, "failed", "Outbox should be FAILED after HTTP error")
        self.assertEqual(outbox.attempt_count, 1, "Attempt count should be incremented")
        self.assertTrue(outbox.last_error, "last_error should be recorded")
        self.assertTrue(outbox.next_attempt_at, "next_attempt_at should be set for retry")

        # Verify keys NOT regenerated
        self.assertEqual(outbox.idempotency_key, idempotency_key,
                         "idempotency_key must be preserved after failure")
        self.assertEqual(outbox.correlation_id, correlation_id,
                         "correlation_id must be preserved after failure")

        # Verify exponential backoff: first retry should have ~60s delay (2^0 * 60)
        time_until_retry = (outbox.next_attempt_at - outbox.create_date).total_seconds()
        self.assertGreater(time_until_retry, 0, "Retry should be scheduled in future")
        # Rough check: should be roughly 60 seconds (first retry: 2^0)
        self.assertTrue(30 < time_until_retry < 120, f"Backoff delay {time_until_retry}s seems wrong")

        # Second attempt: Success (manual advance time and retry)
        outbox.write({"next_attempt_at": False})  # Clear next_attempt_at to allow immediate retry

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "pickup_manifest_id": "pm-retry-001",
            "manifest_no": "MF-RETRY-001",
            "bol_id": "bol-retry-001",
            "geocode_gate": "NEEDS_REVIEW",
        }

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", return_value=mock_success_response):
            outbox._process_one()

        # Refresh and verify retry success

        self.assertEqual(outbox.state, "sent", "Outbox should be SENT after retry success")
        self.assertEqual(outbox.attempt_count, 2, "Attempt count should reflect both attempts")
        self.assertFalse(outbox.last_error, "last_error should be cleared on success")

        # Verify keys still unchanged
        self.assertEqual(outbox.idempotency_key, idempotency_key,
                         "idempotency_key must remain the same across retry")
        self.assertEqual(outbox.correlation_id, correlation_id,
                         "correlation_id must remain the same across retry")

        # Verify IDs populated from retry
        self.assertEqual(outbox.itad_pickup_manifest_id, "pm-retry-001")
        self.assertEqual(order.itad_pickup_manifest_id, "pm-retry-001")

    def test_cron_exponential_backoff_calculation(self):
        """
        Requirement: Exponential backoff formula = min(60 * 2^(attempt_count-1), 3600) seconds.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "itad_core.outbox_backoff_jitter_ratio", "0.0"
        )
        location = self.location
        stage_completed = self.stage_completed

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]

        # Mock failure on each attempt and check backoff progression
        expected_delays = [60, 120, 240, 480, 960, 1920, 3600, 3600]  # capped at 3600

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Server Error"

        with patch("odoo.addons.itad_core.models.itad_outbox.requests.post", return_value=mock_error_response):
            for attempt_idx, expected_delay in enumerate(expected_delays, start=0):
                outbox._process_one()

                if outbox.next_attempt_at:
                    actual_delay = int((outbox.next_attempt_at - outbox.create_date).total_seconds())
                    # Allow ±10% tolerance for test flakiness
                    tolerance = max(int(expected_delay * 0.1), 5)
                    self.assertTrue(
                        abs(actual_delay - expected_delay) <= tolerance,
                        f"Attempt {attempt_idx+1}: expected delay ~{expected_delay}s, got {actual_delay}s"
                    )

                # Clear retry time to allow immediate next attempt
                outbox.write({"next_attempt_at": False})


class TestPhase1CronDomainAndScheduling(TransactionCase):
    """Test: Cron correctly identifies PENDING and due-for-retry FAILED records."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]
        cls.team = _create_team(cls.env)
        cls.location = _create_location(cls.env, cls.team)
        cls.stage_completed = _create_completed_stage(cls.env)

    def test_cron_finds_pending_and_failed_records(self):
        """
        Requirement: Cron domain finds:
        - All records with state='pending'
        - All records with state='failed' AND (next_attempt_at IS NULL OR next_attempt_at <= now)
        """
        location = self.location
        stage_completed = self.stage_completed

        # Create multiple orders with different states
        order1 = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order1.action_submit_pickup_manifest()

        order2 = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order2.action_submit_pickup_manifest()

        outbox1 = self.outbox_model.search([("order_id", "=", order1.id)])[0]
        outbox2 = self.outbox_model.search([("order_id", "=", order2.id)])[0]

        # Set states manually for testing
        outbox1.write({"state": "pending"})  # Should be found
        outbox2.write({
            "state": "failed",
            "next_attempt_at": False,  # Should be found (due for retry)
        })

        # Build cron domain
        from odoo import fields as odoo_fields
        now = odoo_fields.Datetime.now()
        domain = [
            "|",
            ("state", "=", "pending"),
            "&",
            ("state", "=", "failed"),
            "|",
            ("next_attempt_at", "=", False),
            ("next_attempt_at", "<=", now),
        ]

        found = self.outbox_model.search(domain)
        self.assertEqual(len(found), 2, "Cron domain should find both PENDING and due-for-retry FAILED")
        self.assertIn(outbox1.id, found.ids)
        self.assertIn(outbox2.id, found.ids)




