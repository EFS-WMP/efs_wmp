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

from odoo.tests.common import SavepointCase


class TestPhase1ButtonAndOutboxCreation(SavepointCase):
    """Test: Button creates outbox with stable, non-regenerating keys."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]

    def test_button_creates_outbox_pending_with_stable_keys(self):
        """
        Requirement: Clicking "Submit Pickup Manifest" button creates outbox row with stable keys.
        - idempotency_key is generated once and NOT regenerated on repeat clicks
        - correlation_id is generated once and NOT regenerated
        - order.itad_outbox_id points to the same outbox row on retry
        """
        # Create a completed FSM order
        location = self.env.ref("fieldservice.test_location")
        stage_completed = self.env.ref("fieldservice.fsm_stage_completed")

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


class TestPhase1CronPendingToSent(SavepointCase):
    """Test: Cron transitions PENDING → SENT and persists returned IDs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]

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
        location = self.env.ref("fieldservice.test_location")
        stage_completed = self.env.ref("fieldservice.fsm_stage_completed")

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
        }

        # Patch the HTTP call in outbox model
        with patch.object(outbox, "_itad_http_request", return_value=mock_response):
            # Run cron (or call _process_one directly)
            outbox._process_one()

        # Refresh from DB
        outbox.refresh()
        order.refresh()

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
        self.assertEqual(order.itad_submit_state, "sent")

        # Verify keys NOT regenerated
        self.assertEqual(outbox.idempotency_key, idempotency_key,
                         "idempotency_key should NOT change during cron processing")
        self.assertEqual(outbox.correlation_id, correlation_id,
                         "correlation_id should NOT change during cron processing")

    def test_cron_sends_correct_http_headers(self):
        """
        Requirement: HTTP request includes required headers for idempotency.
        """
        location = self.env.ref("fieldservice.test_location")
        stage_completed = self.env.ref("fieldservice.fsm_stage_completed")

        order = self.fsm_order_model.create({
            "location_id": location.id,
            "stage_id": stage_completed.id,
        })
        order.action_submit_pickup_manifest()

        outbox = self.outbox_model.search([("order_id", "=", order.id)])[0]

        # Track headers passed to HTTP call
        captured_headers = {}

        def mock_http_request(url, payload, headers):
            captured_headers.update(headers)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "pickup_manifest_id": "pm-001",
                "manifest_no": "MF-001",
                "bol_id": "bol-001",
            }
            return mock_response

        with patch.object(outbox, "_itad_http_request", side_effect=mock_http_request):
            outbox._process_one()

        # Verify headers
        self.assertIn("Idempotency-Key", captured_headers,
                      "HTTP request must include Idempotency-Key header")
        self.assertEqual(captured_headers["Idempotency-Key"], outbox.idempotency_key)

        self.assertIn("X-Correlation-Id", captured_headers,
                      "HTTP request must include X-Correlation-Id header")
        self.assertEqual(captured_headers["X-Correlation-Id"], outbox.correlation_id)


class TestPhase1CronFailureAndRetry(SavepointCase):
    """Test: Cron handles FAILED with exponential backoff and preserves idempotency_key."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]

    def test_cron_failure_sets_failed_keeps_idempotency_key_and_retry_succeeds(self):
        """
        Requirement: On HTTP failure:
        - Outbox transitions to FAILED (not SENT)
        - idempotency_key and correlation_id are NOT regenerated
        - last_error is recorded
        - next_attempt_at is set (exponential backoff)
        - On next cron run: retry reuses same keys and succeeds
        """
        location = self.env.ref("fieldservice.test_location")
        stage_completed = self.env.ref("fieldservice.fsm_stage_completed")

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

        with patch.object(outbox, "_itad_http_request", return_value=mock_error_response):
            outbox._process_one()

        # Refresh and verify failure state
        outbox.refresh()
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

        with patch.object(outbox, "_itad_http_request", return_value=mock_success_response):
            outbox._process_one()

        # Refresh and verify retry success
        outbox.refresh()
        order.refresh()

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
        location = self.env.ref("fieldservice.test_location")
        stage_completed = self.env.ref("fieldservice.fsm_stage_completed")

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

        with patch.object(outbox, "_itad_http_request", return_value=mock_error_response):
            for attempt_idx, expected_delay in enumerate(expected_delays, start=0):
                outbox._process_one()
                outbox.refresh()

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


class TestPhase1CronDomainAndScheduling(SavepointCase):
    """Test: Cron correctly identifies PENDING and due-for-retry FAILED records."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_order_model = cls.env["fsm.order"]
        cls.outbox_model = cls.env["itad.core.outbox"]

    def test_cron_finds_pending_and_failed_records(self):
        """
        Requirement: Cron domain finds:
        - All records with state='pending'
        - All records with state='failed' AND (next_attempt_at IS NULL OR next_attempt_at <= now)
        """
        location = self.env.ref("fieldservice.test_location")
        stage_completed = self.env.ref("fieldservice.fsm_stage_completed")

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
