# File: itad_core/models/itad_outbox.py

import hashlib
import json
import logging
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class ItadCoreOutbox(models.Model):
    _name = "itad.core.outbox"
    _description = "ITAD Core Outbox"
    _order = "create_date asc"
    _rec_name = "idempotency_key"

    order_id = fields.Many2one("fsm.order", required=True, ondelete="cascade", index=True)

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("dead_letter", "Dead Letter"),
        ],
        default="pending",
        required=True,
        index=True,
    )

    idempotency_key = fields.Char(required=True, readonly=True, index=True)
    correlation_id = fields.Char(required=True, readonly=True, index=True)

    payload_json = fields.Text(readonly=True)
    payload_sha256 = fields.Char(readonly=True)

    attempt_count = fields.Integer(default=0, readonly=True)
    next_attempt_at = fields.Datetime(readonly=True)
    next_retry_at = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)
    last_http_status = fields.Integer(readonly=True)
    dead_letter_reason = fields.Char(readonly=True)

    # Response snapshot (optional but handy for UI/debug)
    itad_pickup_manifest_id = fields.Char(readonly=True)
    itad_manifest_no = fields.Char(readonly=True)
    itad_status = fields.Char(readonly=True)
    itad_bol_id = fields.Char(readonly=True)
    itad_geocode_gate = fields.Char(readonly=True)
    itad_receiving_id = fields.Char(readonly=True)
    itad_receiving_weight_record_id = fields.Char(
        related="order_id.itad_receiving_weight_record_id",
        readonly=True,
    )

    def _get_config(self):
        # Expect config model to return (base_url, token)
        return self.env["itad.core.config"].get_itad_core_config()

    def _get_retry_config(self):
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "max_attempts": int(icp.get_param("itad_core.outbox_max_attempts", "5")),
            "base_delay_seconds": int(icp.get_param("itad_core.outbox_backoff_base_seconds", "60")),
            "max_delay_seconds": int(icp.get_param("itad_core.outbox_max_delay_seconds", "3600")),
            "jitter_ratio": float(icp.get_param("itad_core.outbox_backoff_jitter_ratio", "0.25")),
        }

    def _deterministic_jitter(self, base_delay, attempt):
        if not self.idempotency_key:
            return 0
        raw = f"{self.idempotency_key}:{attempt}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        jitter_range = max(1, int(base_delay * self._get_retry_config()["jitter_ratio"]))
        return int(digest, 16) % (jitter_range + 1)

    def _compute_next_retry_at(self, attempt):
        retry_config = self._get_retry_config()
        base_delay = retry_config["base_delay_seconds"]
        delay = base_delay * (2 ** max(attempt - 1, 0))
        delay = min(delay, retry_config["max_delay_seconds"])
        delay += self._deterministic_jitter(base_delay, attempt)
        return fields.Datetime.now() + timedelta(seconds=delay)

    def _is_retryable_status(self, status_code):
        if status_code is None:
            return True
        if status_code >= 500:
            return True
        if status_code in (408, 429):
            return True
        if 400 <= status_code < 500:
            return False
        return True

    @api.model
    def _map_outbox_state_to_submit_state(self, outbox_state):
        mapping = {
            "pending": "pending",
            "sent": "sent",
            "failed": "failed",
            "dead_letter": "failed",
        }
        return mapping.get(outbox_state, "failed")

    def _write_order_telemetry(self, order, vals):
        order.sudo().with_context(
            itad_telemetry_write=True,
            mail_notrack=True,
            tracking_disable=True,
        ).write(vals)

    def _send_to_itad_core(self):
        self.ensure_one()
        if not self.payload_json:
            raise UserError(_("Missing payload_json."))

        base_url, token = self._get_config()
        url = base_url.rstrip("/") + "/api/v1/pickup-manifests:submit"

        headers = {
            "Idempotency-Key": self.idempotency_key,
            "X-Correlation-Id": self.correlation_id,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = json.loads(self.payload_json)
        if "manifest_fingerprint" not in payload:
            payload["manifest_fingerprint"] = self.payload_sha256
        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if 200 <= resp.status_code < 300:
            return resp.json(), resp.status_code, resp.text
        return None, resp.status_code, resp.text

    def _record_success(self, data: dict, status_code=None):
        now = fields.Datetime.now()
        receiving_weight_record_id = data.get("receiving_weight_record_id") or data.get("receiving_id")
        self.write(
            {
                "state": "sent",
                "attempt_count": self.attempt_count + 1,
                "next_attempt_at": False,
                "next_retry_at": False,
                "last_error": False,
                "last_http_status": status_code,
                "dead_letter_reason": False,
                "itad_pickup_manifest_id": data.get("pickup_manifest_id"),
                "itad_manifest_no": data.get("manifest_no"),
                "itad_status": data.get("status"),
                "itad_bol_id": data.get("bol_id"),
                "itad_geocode_gate": data.get("geocode_gate"),
                "itad_receiving_id": data.get("receiving_id"),
            }
        )

        # Phase 1: FSM is SoR; update read-only ITAD refs on order
        order_vals = {
            "itad_submit_state": "sent",
            "itad_pickup_manifest_id": data.get("pickup_manifest_id"),
            "itad_manifest_no": data.get("manifest_no"),
            "itad_manifest_status": data.get("status"),
            "itad_bol_id": data.get("bol_id"),
            "itad_geocode_gate": data.get("geocode_gate"),
            "itad_last_submit_at": now,
            "itad_last_error": False,
            "itad_outbox_id": self.id,
            "itad_outbox_last_id": self.id,
            "itad_receipt_state": "pending",  # Phase 2.1: Ready for receiving confirmation
        }
        if receiving_weight_record_id:
            order_vals["itad_receiving_weight_record_id"] = receiving_weight_record_id
            if "itad_receiving_id" in self.order_id._fields and not self.order_id.itad_receiving_id:
                order_vals["itad_receiving_id"] = data.get("receiving_id") or receiving_weight_record_id
        self._write_order_telemetry(self.order_id, order_vals)

    def _record_failure(self, error_message: str, status_code=None):
        now = fields.Datetime.now()
        attempt = self.attempt_count + 1
        retry_config = self._get_retry_config()
        max_attempts = retry_config["max_attempts"]
        next_retry_at = self._compute_next_retry_at(attempt)
        next_attempt = next_retry_at
        retryable = self._is_retryable_status(status_code)
        should_dead_letter = (attempt >= max_attempts) or not retryable
        state = "dead_letter" if should_dead_letter else "failed"
        dead_letter_reason = False
        if should_dead_letter:
            if not retryable:
                dead_letter_reason = f"non_retryable_status:{status_code}"
            else:
                dead_letter_reason = "max_attempts_exceeded"
            next_attempt = False
            next_retry_at = False

        self.write(
            {
                "state": state,
                "attempt_count": attempt,
                "next_attempt_at": next_attempt,
                "next_retry_at": next_retry_at,
                "last_error": error_message,
                "last_http_status": status_code,
                "dead_letter_reason": dead_letter_reason,
            }
        )

        self._write_order_telemetry(
            self.order_id,
            {
                "itad_submit_state": "failed",
                "itad_last_error": error_message,
                "itad_last_submit_at": now,
                "itad_outbox_id": self.id,
                "itad_outbox_last_id": self.id,
            },
        )

    def _process_one(self):
        self.ensure_one()
        _logger.info(
            "ITAD outbox attempt: id=%s order=%s state=%s attempt=%s",
            self.id,
            self.order_id.id,
            self.state,
            self.attempt_count + 1,
        )
        try:
            data, status_code, response_text = self._send_to_itad_core()
            if data:
                self._record_success(data, status_code=status_code)
                _logger.info(
                    "ITAD outbox sent: id=%s order=%s status=%s",
                    self.id,
                    self.order_id.id,
                    status_code,
                )
            else:
                error_message = _("ITAD Core error %(status)s: %(body)s") % {
                    "status": status_code,
                    "body": response_text,
                }
                self._record_failure(error_message, status_code=status_code)
                _logger.warning(
                    "ITAD outbox failed: id=%s order=%s status=%s",
                    self.id,
                    self.order_id.id,
                    status_code,
                )
        except Exception as exc:
            self._record_failure(str(exc))
            _logger.exception(
                "ITAD outbox exception: id=%s order=%s error=%s",
                self.id,
                self.order_id.id,
                exc,
            )

    def action_retry(self):
        return self.action_requeue()

    def action_requeue(self):
        if not self.env.user.has_group("itad_core.group_receiving_manager"):
            raise AccessError(_("Only receiving managers can requeue outbox records."))
        now = fields.Datetime.now()
        for rec in self:
            rec.write(
                {
                    "state": "pending",
                    "attempt_count": 0,
                    "next_attempt_at": now,
                    "next_retry_at": now,
                    "last_error": False,
                    "last_http_status": False,
                    "dead_letter_reason": False,
                }
            )
            self._write_order_telemetry(
                rec.order_id,
                {
                    "itad_submit_state": "pending",
                    "itad_last_error": False,
                    "itad_outbox_id": rec.id,
                    "itad_outbox_last_id": rec.id,
                },
            )
        return True

    @api.model
    def _cron_process_itad_outbox(self):
        now = fields.Datetime.now()
        records = self.search(
            [
                "|",
                ("state", "=", "pending"),
                "&",
                ("state", "=", "failed"),
                "|",
                ("next_retry_at", "<=", now),
                "&",
                ("next_retry_at", "=", False),
                "|",
                ("next_attempt_at", "=", False),
                ("next_attempt_at", "<=", now),
            ],
            order="create_date asc",
        )
        for rec in records:
            rec._process_one()
        return True
